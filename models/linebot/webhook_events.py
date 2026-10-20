"""Transactional event inbox; reply delivery happens only after the caller commits."""
import json
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from linebot.v3.messaging import FlexMessage
from ..idempotency import fingerprint, IdempotencyConflict
from ..schema import line_webhook_events_table


class LineWebhookEvents:
    def __init__(self, db_session):
        self.db_session = db_session

    def process(self, event, handler):
        event_id = getattr(event, 'webhook_event_id', None)
        if not event_id or len(event_id) > 255:
            raise ValueError('LINE event ID is required')
        message, postback = getattr(event, 'message', None), getattr(event, 'postback', None)
        payload = dict(type=event.type, source=event.source.to_dict() if event.source else None,
                       message={k: getattr(message, k, None) for k in ('id', 'type', 'text')} if message else None,
                       postback=dict(data=postback.data, params=postback.params) if postback else None)
        # Reply tokens and isRedelivery change on delivery retries; neither is
        # part of the immutable event identity or persisted response.
        digest = fingerprint(payload)
        table = line_webhook_events_table
        with self.db_session.begin_nested():
            self.db_session.execute(insert(table).values(event_id=event_id, payload_hash=digest)
                .on_conflict_do_nothing(index_elements=['event_id']))
            row = self.db_session.execute(select(table).where(table.c.event_id == event_id).with_for_update()).mappings().one()
            if row['payload_hash'] != digest:
                raise IdempotencyConflict('LINE event payload changed')
            if row['reply_payload'] is not None:
                saved = row['reply_payload']
            else:
                response = handler(event)
                saved = ({'text': response} if isinstance(response, str) else
                         {'flex': json.loads(response.to_json())} if response is not None else {})
                self.db_session.execute(update(table).where(table.c.event_id == event_id).values(reply_payload=saved))
        return saved.get('text') if 'text' in saved else FlexMessage.from_dict(saved['flex']) if 'flex' in saved else None
