"""Persist LINE previews; only an owner-bound confirmation may create a ledger row."""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, update
from ..ai_parse_event_manager import AIParseEventManager
from ..asset_manager import AssetManager
from ..budget_manager import BudgetManager, InsufficientBalanceError
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

    @staticmethod
    def _account_problem(found, payload):
        """Why the account frozen into a draft can no longer take the entry, in words the person can act on."""
        if found is None or found['deleted_at'] is not None:
            return '這個帳戶已經不存在，沒有新增記帳。請重新傳一次這筆，並選擇其他帳戶。'
        name = found['name']
        if not found['is_active']:
            return f'帳戶「{name}」已被停用或封存，沒有新增記帳。請重新傳一次這筆，並選擇其他帳戶。'
        if not found['track_balance']:
            return f'帳戶「{name}」不追蹤餘額，LINE 無法記到這個帳戶，沒有新增記帳。請重新傳一次這筆並改選其他帳戶，或到 Nomica Web 記帳。'
        if found['currency'] != payload.get('original_currency'):
            return (f"帳戶「{name}」的幣別是 {found['currency']}，這筆是 {payload.get('original_currency')}，"
                    '沒有新增記帳。請重新傳一次這筆，並選擇同幣別的帳戶。')
        return None

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
            return '這則訊息沒有解析成可記帳的內容，沒有新增記帳。請重新傳一筆收支，例如「午餐 120」。'
        created_at = row['created_at']
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        expired = datetime.now(timezone.utc) - created_at > self.ttl
        if action == 'cancel' or expired:
            self.db_session.execute(update(table).where(table.c.id == key).values(status='cancelled'))
            if action == 'cancel':
                return '已取消這筆草稿，沒有新增記帳。'
            return '這份草稿已超過 30 分鐘，沒有新增記帳。請重新傳一次這筆收支。'
        if action != 'confirm':
            return '請使用草稿上的確認或取消按鈕。'
        # Recheck the frozen account under lock before a pilot can write money.
        account = accounts_table
        found = self.db_session.execute(select(
            account.c.name, account.c.deleted_at, account.c.is_active, account.c.track_balance, account.c.currency,
        ).where(account.c.id == payload.get('account_id'), account.c.user_id == owner).with_for_update()).mappings().first()
        problem = self._account_problem(found, payload)
        if problem:
            return problem
        if payload.get('amount') is None or payload.get('date') is None:
            return '這筆草稿缺少金額或日期，沒有新增記帳。請重新傳一次，例如「午餐 120」。'
        # Row lock + stable transaction key protect even distinct postback event
        # IDs clicking the same preview concurrently across multiple workers.
        transaction = {**payload, 'client_request_id': str(key)}
        try:
            category_id = self.service.budget_manager._get_category_id(
                owner, payload['budget_category'], payload['type'],
            )
        except ValueError:
            return f"分類「{payload['budget_category']}」已經無法使用，沒有新增記帳。請重新傳一次這筆。"
        if str(category_id) != row['parsed_payload'].get('category_id'):
            return '這筆的分類在你確認前被改過，沒有新增記帳。請重新傳一次這筆。'
        try:
            with self.db_session.begin_nested():
                result = self.service.create_transaction(user_id, transaction)
                if not result['success']:
                    raise ValueError(result['message'])
        except InsufficientBalanceError as error:
            return f"{error}\n補記之後，請重新傳一次這筆（例如「午餐 120」）。"
        except ValueError as error:
            # Validation messages from the ledger are written for people; database errors are not ValueErrors.
            reason = str(error).strip()[:80]
            return f"沒有新增記帳：{reason}。請重新傳一次這筆，或到 Nomica Web 記帳。" if reason \
                else '沒有新增記帳。請重新傳一次這筆，或到 Nomica Web 記帳。'
        if not result['success']:
            raise ValueError(result['message'])
        self.events.confirm_event(user_id, key, payload['type'], result['transaction_id'])
        return f"記帳完成：{payload['item']} {payload['amount']} {payload['original_currency']}。"
