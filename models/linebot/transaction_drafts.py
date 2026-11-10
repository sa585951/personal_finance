"""Persist LINE previews; only an owner-bound confirmation may create a ledger row."""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, update
from ..ai_parse_event_manager import AIParseEventManager
from ..asset_manager import AssetManager
from ..budget_manager import BudgetManager
from ..idempotency import money
from ..schema import accounts_table, ai_parse_events_table
from ..transaction_service import TransactionService
from .line_sdk import FlexSendMessage


class LineTransactionDrafts:
    ttl = timedelta(minutes=30)

    def __init__(self, db_session):
        self.db_session = db_session
        self.assets = AssetManager(db_session)
        self.service = TransactionService(BudgetManager(db_session), self.assets)
        self.events = AIParseEventManager(db_session)

    def preview(self, draft_id, payload, account_label):
        prefix = 'nomica.oral.'
        return FlexSendMessage(alt_text='確認收支：尚未記帳', contents={
            'type': 'bubble', 'body': {'type': 'box', 'layout': 'vertical', 'contents': [
                {'type': 'text', 'text': '確認收支（尚未記帳）', 'weight': 'bold', 'wrap': True},
                {'type': 'text', 'text': f"{payload['date']} · {payload['item']}\n{'收入' if payload['type']=='income' else '支出'} {payload['amount']} {payload['original_currency']}\n分類：{payload["budget_category"]}\n帳戶：{account_label}", 'wrap': True, 'margin': 'md'},
                {'type': 'text', 'text': '請核對金額、日期與帳戶；30分鐘內確認才會記帳。要改金額請回「改金額 150」，其他資料不正確請取消並重新輸入。', 'size': 'sm', 'wrap': True, 'margin': 'md'},
            ]}, 'footer': {'type': 'box', 'layout': 'vertical', 'contents': [
                {'type': 'button', 'style': 'primary', 'action': {'type': 'postback', 'label': '確認新增', 'data': f'{prefix}confirm:{draft_id}'}},
                {'type': 'button', 'action': {'type': 'postback', 'label': '取消', 'data': f'{prefix}cancel:{draft_id}'}},
                {'type': 'button', 'style': 'secondary', 'action': {'type': 'postback', 'label': '改分類', 'data': f'{prefix}cats:{draft_id}'}},
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
        if row is None or not (row['parsed_payload'] or {}).get('line_oral'):
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
        # Recheck the frozen account under lock before a pilot can write money.
        account = accounts_table
        eligible = self.db_session.execute(select(account.c.id).where(
            account.c.id == payload.get('account_id'), account.c.user_id == owner,
            account.c.deleted_at.is_(None), account.c.is_active.is_(True),
            account.c.track_balance.is_(True), account.c.currency == payload['original_currency'],
        ).with_for_update()).first()
        if not eligible or payload.get('amount') is None or payload.get('date') is None:
            return '草稿資料不完整或帳戶已無法使用，請重新輸入。'
        # Row lock + stable transaction key protect even distinct postback event
        # IDs clicking the same preview concurrently across multiple workers.
        transaction = {**payload, 'client_request_id': str(key)}
        try:
            with self.db_session.begin_nested():
                category_id = self.service.budget_manager._get_category_id(
                    owner, payload['budget_category'], payload['type'],
                )
                if str(category_id) != row['parsed_payload'].get('category_id'):
                    return '草稿分類已變更，請重新輸入。'
                result = self.service.create_transaction(user_id, transaction)
                if not result['success']:
                    raise ValueError(result['message'])
        except ValueError:
            return '目前無法入帳，請核對帳戶餘額與草稿資料後再試。'
        if not result['success']:
            raise ValueError(result['message'])
        self.events.confirm_event(user_id, key, payload['type'], result['transaction_id'])
        return f"記帳完成：{payload['item']} {payload['amount']} {payload['original_currency']}。"
