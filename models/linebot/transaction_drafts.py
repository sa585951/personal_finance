"""Persist LINE previews; only an owner-bound confirmation may create a ledger row."""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, update
from ..ai_parse_event_manager import AIParseEventManager
from ..asset_manager import AssetManager
from ..budget_manager import BudgetManager
from ..idempotency import money
from ..schema import ai_parse_events_table
from ..transaction_service import TransactionService
from .line_sdk import FlexSendMessage


class LineTransactionDrafts:
    ttl = timedelta(minutes=30)

    def __init__(self, db_session):
        self.db_session = db_session
        self.assets = AssetManager(db_session)
        self.service = TransactionService(BudgetManager(db_session), self.assets)
        self.events = AIParseEventManager(db_session)

    def prepare(self, user_id, parsed):
        legacy = parsed['legacy']
        if parsed.get('errors') or parsed.get('missing_fields'):
            return '解析資料不完整，尚未建立收支。請補齊資料後重新輸入。'
        asset = self.service._find_asset(user_id, legacy.get('target_asset'), legacy, parsed.get('raw_text', ''))
        if legacy.get('target_asset') and not asset:
            return '找不到指定帳戶，尚未建立收支。請確認帳戶名稱後重新輸入。'
        payload = dict(
            date=self.service._transaction_date(legacy), item=legacy.get('category') or '記帳',
            amount=money(legacy.get('amount')), type=legacy['type'],
            budget_category=legacy.get('budget_category'), description=legacy.get('description') or '',
            account_id=str(asset['id']) if asset else None,
            original_currency=legacy.get('currency') or (asset['currency'] if asset else 'TWD'),
        )
        # Freeze date/account/currency in the DB preview; a later worker must not
        # reparse or resolve a different account when the user confirms.
        record = self.events.record_from_parse_result(user_id, 'line_bot', {**parsed, 'line_draft': payload})
        draft_id = str(record['id'])
        account_label = asset['bank_name'] if asset else '不連動帳戶'
        return FlexSendMessage(alt_text='確認收支：尚未記帳', contents={
            'type': 'bubble', 'body': {'type': 'box', 'layout': 'vertical', 'contents': [
                {'type': 'text', 'text': '確認收支（尚未記帳）', 'weight': 'bold', 'wrap': True},
                {'type': 'text', 'text': f"{payload['date']} · {payload['item']}\n{'收入' if payload['type']=='income' else '支出'} {payload['amount']} {payload['original_currency']}\n帳戶：{account_label}", 'wrap': True, 'margin': 'md'},
                {'type': 'text', 'text': '請核對金額、日期與帳戶；30分鐘內確認才會記帳。資料不正確請取消並重新輸入。', 'size': 'sm', 'wrap': True, 'margin': 'md'},
            ]}, 'footer': {'type': 'box', 'layout': 'vertical', 'contents': [
                {'type': 'button', 'style': 'primary', 'action': {'type': 'postback', 'label': '確認新增', 'data': 'nomica.confirm:'+draft_id}},
                {'type': 'button', 'action': {'type': 'postback', 'label': '取消', 'data': 'nomica.cancel:'+draft_id}},
            ]},
        })

    def resolve(self, user_id, draft_id, action):
        try:
            owner, key = UUID(str(user_id)), UUID(str(draft_id))
        except (ValueError, TypeError):
            return '找不到可操作的收支草稿，請重新輸入。'
        table = ai_parse_events_table
        row = self.db_session.execute(select(table).where(
            table.c.id == key, table.c.user_id == owner, table.c.source == 'line_bot',
        ).with_for_update()).mappings().first()
        if row is None:
            return '找不到可操作的收支草稿，請重新輸入。'
        if row['status'] == 'confirmed':
            return '這筆收支先前已建立，沒有再次記帳或扣款。'
        if row['status'] == 'cancelled':
            return '這份收支草稿已取消，沒有新增記帳。'
        payload = (row['parsed_payload'] or {}).get('line_draft')
        if row['status'] != 'success' or not payload:
            return '這份資料不能確認記帳，請重新輸入。'
        created_at = row['created_at']
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if action == 'cancel' or datetime.now(timezone.utc) - created_at > self.ttl:
            self.db_session.execute(update(table).where(table.c.id == key).values(status='cancelled'))
            return '收支草稿已取消或逾期，沒有新增記帳。'
        if action != 'confirm':
            return '請使用草稿上的確認或取消按鈕。'
        # Row lock + stable transaction key protect even distinct postback event
        # IDs clicking the same preview concurrently across multiple workers.
        result = self.service.create_transaction(user_id, {**payload, 'client_request_id': str(key)})
        if not result['success']:
            raise ValueError(result['message'])
        self.events.confirm_event(user_id, key, payload['type'], result['transaction_id'])
        return f"記帳完成：{payload['item']} {payload['amount']} {payload['original_currency']}。"
