# models/linebot/message_handler.py

from datetime import datetime
from zoneinfo import ZoneInfo
# 移除簡單的 Handler 導入，因為我們會將其邏輯直接整合進來
# from .handlers import ExpenseHandler, IncomeHandler, QueryHandler, AssetHandler, GoalHandler

# 導入我們需要的 Manager 類別
from ..budget_manager import BudgetManager
from ..asset_manager import AssetManager

# 導入 Flow Handlers
from .flow_handlers.transfer_flow_handler import TransferFlowHandler
from .flow_handlers.add_account_flow_handler import AddAccountFlowHandler
from .flow_handlers.update_balance_flow_handler import UpdateBalanceFlowHandler
from .flow_handlers.delete_asset_flow_handler import DeleteAssetFlowHandler
from .flow_handlers.delete_transaction_flow_handler import DeleteTransactionFlowHandler
from .flow_handlers.add_expense_flow_handler import AddExpenseFlowHandler
from .flow_handlers.add_income_flow_handler import AddIncomeFlowHandler
from .flow_handlers.set_budget_flow_handler import SetBudgetFlowHandler
from .response_builder import ResponseBuilder

class MessageHandler:
    DEFAULT_TRANSACTION_TIMEZONE = "Asia/Taipei"

    """訊息處理器 - 負責訊息路由和處理邏輯"""
    def __init__(self, user_state_manager, db_session):
        self.user_state_manager = user_state_manager
        self.db_session = db_session
        self.response_builder = ResponseBuilder()
        operation_theme = self.response_builder.operation_theme

        # 初始化資料管理器
        self.budget_manager = BudgetManager(db_session)
        self.asset_manager = AssetManager(db_session)

        # 初始化流程處理器，並傳入 manager
        self.flow_handlers = {
            "transfer_flow": TransferFlowHandler(self.user_state_manager, operation_theme, self.asset_manager),
            "add_account_flow": AddAccountFlowHandler(self.user_state_manager, operation_theme, self.asset_manager),
            "update_balance_flow": UpdateBalanceFlowHandler(self.user_state_manager, operation_theme, self.asset_manager),
            "delete_asset_flow": DeleteAssetFlowHandler(self.user_state_manager, operation_theme, self.asset_manager),
            "delete_transaction_flow": DeleteTransactionFlowHandler(self.user_state_manager, operation_theme, self.budget_manager),
            "add_expense_flow": AddExpenseFlowHandler(self.user_state_manager, operation_theme, self.budget_manager, self.asset_manager),
            "add_income_flow": AddIncomeFlowHandler(self.user_state_manager, operation_theme, self.budget_manager, self.asset_manager),
            "set_budget_flow": SetBudgetFlowHandler(self.user_state_manager, operation_theme, self.budget_manager),
        }

    def handle_user_message(self, user_id, message, parsed_data):
        """處理用戶訊息的主要入口"""
        user_state = self.user_state_manager.get_user_state(user_id)
        if user_state:
            return self._handle_flow_message(user_id, message, user_state)
        
        return self._handle_parsed_message(user_id, parsed_data)
    
    def handle_postback(self, user_id, data, params):
        """處理 Postback 事件"""
        user_state = self.user_state_manager.get_user_state(user_id)
        if user_state:
            # 如果有進行中的流程，將 Postback 資料視為輸入
            # 我們將 params 合併到 message 中，或者特殊處理
            # 對於 DatetimePicker，params 會有 'date', 'time' 或 'datetime'
            
            message = data # 預設使用 data 作為訊息
            
            # 如果是日期選擇器回傳
            if params:
                if 'date' in params:
                    message = params['date']
                elif 'time' in params:
                    message = params['time']
                elif 'datetime' in params:
                    message = params['datetime']
            
            return self._handle_flow_message(user_id, message, user_state)
        
        return None
    
    def _handle_flow_message(self, user_id, message, user_state):
        """處理流程中的訊息"""
        state_type = user_state.get("type")
        handler = self.flow_handlers.get(state_type)
        
        if handler:
            return handler.handle_flow_message(user_id, message, user_state)
        else:
            self.user_state_manager.clear_user_state(user_id)
            return "操作流程已重置，請重新開始"
        
    def _handle_parsed_message(self, user_id, parsed_data):
        """處理解析後的訊息"""
        message_type = parsed_data.get("type")
        
        if message_type == "expense":
            return self._handle_expense(parsed_data, user_id)
        elif message_type == "income":
            return self._handle_income(parsed_data, user_id)
        elif message_type == "query":
            return self._handle_query(user_id)
        elif message_type == "asset_query":
            return self._handle_asset_query(user_id)
        elif message_type == "help":
            return self._get_help_message()
        elif message_type == "other" and parsed_data.get("error") == "unrecognized_input":
            return self.response_builder.create_unrecognized_input_message()
        elif message_type in {
            "goal_query",
            "manage_goal",
            "goal_progress",
            "start_add_goal",
            "start_edit_goal",
            "start_delete_goal",
        }:
            return self._handle_goal_unavailable()
        
        elif message_type.startswith("start_"):
            flow_type = message_type.replace("start_", "") + "_flow"
            handler = self.flow_handlers.get(flow_type)
            if handler:
                return handler.start_flow(user_id)
        
        return self._get_help_message()
        
    def _handle_expense(self, parsed_data, user_id):
        """處理支出記錄並更新資產餘額"""
        try:
            target_asset_name = parsed_data.get("target_asset")
            asset = None
            if target_asset_name:
                asset = self.asset_manager.find_asset_by_name(
                    user_id,
                    target_asset_name,
                    currency=parsed_data.get("currency"),
                )

            # 1. 新增交易紀錄
            self.budget_manager.add_transaction(
                user_id, self._transaction_date(parsed_data),
                parsed_data['category'], parsed_data['amount'], 'expense',
                parsed_data['budget_category'], parsed_data.get('description', ''),
                account_id=asset["account_key"] if asset else None,
                original_currency=parsed_data.get("currency") or (asset["currency"] if asset else None),
            )

            # 2. 帳戶餘額已由 BudgetManager 依 account_id 同步更新，避免交易與餘額狀態分離。
            asset_update_msg = None
            if target_asset_name:
                if asset:
                    asset_update_msg = f"已從 {asset['bank_name']} 扣款"
                else:
                    asset_update_msg = f"找不到名為 {target_asset_name} 的資產"
            
            response_data = {
                "category": parsed_data["category"],
                "amount": parsed_data["amount"],
                "description": parsed_data.get("description") or "",
                "date": self._transaction_date(parsed_data),
                "account_message": asset_update_msg,
            }
            return self.response_builder.create_expense_success(response_data)
        except Exception as e:
            return self.response_builder.create_error_message(f"紀錄失敗: {e}")

    def _handle_income(self, parsed_data, user_id):
        """處理收入記錄並更新資產餘額"""
        try:
            target_asset_name = parsed_data.get("target_asset")
            asset = None
            if target_asset_name:
                asset = self.asset_manager.find_asset_by_name(
                    user_id,
                    target_asset_name,
                    currency=parsed_data.get("currency"),
                )

            # 1. 新增交易紀錄
            self.budget_manager.add_transaction(
                user_id, self._transaction_date(parsed_data),
                parsed_data['category'], parsed_data['amount'], 'income',
                parsed_data['budget_category'], parsed_data.get('description', ''),
                account_id=asset["account_key"] if asset else None,
                original_currency=parsed_data.get("currency") or (asset["currency"] if asset else None),
            )

            # 2. 帳戶餘額已由 BudgetManager 依 account_id 同步更新，避免交易與餘額狀態分離。
            asset_update_msg = None
            if target_asset_name:
                if asset:
                    asset_update_msg = f"已存入 {asset['bank_name']}"
                else:
                    asset_update_msg = f"找不到名為 {target_asset_name} 的資產"

            response_data = {
                "amount": parsed_data["amount"],
                "description": parsed_data.get("description") or "",
                "date": self._transaction_date(parsed_data),
                "account_message": asset_update_msg,
            }
            return self.response_builder.create_income_success(response_data)
        except Exception as e:
            return self.response_builder.create_error_message(f"紀錄失敗: {e}")

    def _transaction_date(self, parsed_data):
        parsed_date = parsed_data.get("date")
        if parsed_date:
            return parsed_date
        return datetime.now(ZoneInfo(self.DEFAULT_TRANSACTION_TIMEZONE)).strftime("%Y-%m-%d")
    
    def _handle_query(self, user_id):
        """處理查詢請求"""
        try:
            month = datetime.now().strftime("%Y-%m")
            total_expenses = sum(self.budget_manager.calculate_monthly_expenses(user_id, month).values())
            transactions = self.budget_manager.get_all_transactions(user_id)
            
            # 處理 date 可能是 datetime.date 物件或字串的情況
            def get_date_str(transaction):
                date_val = transaction['date']
                if isinstance(date_val, str):
                    return date_val
                # 如果是 datetime.date 物件，轉換為字串
                return date_val.strftime("%Y-%m-%d") if hasattr(date_val, 'strftime') else str(date_val)
            
            recent_transactions = [t for t in transactions if get_date_str(t).startswith(month)][:5]
            transaction_count = len([t for t in transactions if get_date_str(t).startswith(month)])
            
            return self.response_builder.create_monthly_summary(
                month, total_expenses, transaction_count, recent_transactions, {}
            )
        except Exception as e:
            return self.response_builder.create_error_message(f"查詢失敗: {e}")
    
    def _handle_asset_query(self, user_id):
        """處理資產查詢"""
        try:
            totals = self.asset_manager.calculate_totals(user_id)
            return self.response_builder.create_asset_overview(totals)
        except Exception as e:
            return self.response_builder.create_error_message(f"查詢資產失敗: {e}")
    
    def _handle_goal_unavailable(self):
        """財務目標目前已從 MVP LINE 流程暫停。"""
        return self.response_builder.create_goal_unavailable()
    
    def _get_help_message(self):
        """取得幫助訊息"""
        return self.response_builder.create_help_message()
