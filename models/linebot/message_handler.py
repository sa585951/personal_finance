# models/linebot/message_handler.py

from datetime import datetime
# 移除簡單的 Handler 導入，因為我們會將其邏輯直接整合進來
# from .handlers import ExpenseHandler, IncomeHandler, QueryHandler, AssetHandler, GoalHandler

# 導入我們需要的 Manager 類別
from ..budget_manager import BudgetManager
from ..asset_manager import AssetManager
from ..goal_manager import GoalManager

# 導入 Flow Handlers
from .flow_handlers.transfer_flow_handler import TransferFlowHandler
from .flow_handlers.add_account_flow_handler import AddAccountFlowHandler
from .flow_handlers.update_balance_flow_handler import UpdateBalanceFlowHandler
from .flow_handlers.delete_asset_flow_handler import DeleteAssetFlowHandler
from .flow_handlers.delete_transaction_flow_handler import DeleteTransactionFlowHandler
from .flow_handlers.add_goal_flow_handler import AddGoalFlowHandler
from .flow_handlers.add_expense_flow_handler import AddExpenseFlowHandler
from .flow_handlers.add_income_flow_handler import AddIncomeFlowHandler
from .flow_handlers.edit_goal_flow_handler import EditGoalFlowHandler
from .flow_handlers.delete_goal_flow_handler import DeleteGoalFlowHandler
from .response_builder import ResponseBuilder

class MessageHandler:
    """訊息處理器 - 負責訊息路由和處理邏輯"""
    def __init__(self, user_state_manager):
        self.user_state_manager = user_state_manager
        self.response_builder = ResponseBuilder()
        operation_theme = self.response_builder.operation_theme

        # 初始化流程處理器，不再傳入 manager
        self.flow_handlers = {
            "transfer_flow": TransferFlowHandler(self.user_state_manager, operation_theme),
            "add_account_flow": AddAccountFlowHandler(self.user_state_manager, operation_theme),
            "update_balance_flow": UpdateBalanceFlowHandler(self.user_state_manager, operation_theme),
            "delete_asset_flow": DeleteAssetFlowHandler(self.user_state_manager, operation_theme),
            "delete_transaction_flow": DeleteTransactionFlowHandler(self.user_state_manager, operation_theme),
            "add_goal_flow": AddGoalFlowHandler(self.user_state_manager, operation_theme),
            "add_expense_flow": AddExpenseFlowHandler(self.user_state_manager, operation_theme),
            "add_income_flow": AddIncomeFlowHandler(self.user_state_manager, operation_theme),
            "edit_goal_flow": EditGoalFlowHandler(self.user_state_manager, operation_theme),
            "delete_goal_flow": DeleteGoalFlowHandler(self.user_state_manager, operation_theme),
        }

    def handle_user_message(self, user_id, message, parsed_data, db_session):
        """處理用戶訊息的主要入口，現在接收 db_session"""
        user_state = self.user_state_manager.get_user_state(user_id)
        if user_state:
            return self._handle_flow_message(user_id, message, user_state, db_session)
        
        return self._handle_parsed_message(user_id, parsed_data, db_session)
    
    def _handle_flow_message(self, user_id, message, user_state, db_session):
        """處理流程中的訊息，傳遞 db_session"""
        state_type = user_state.get("type")
        handler = self.flow_handlers.get(state_type)
        
        if handler:
            return handler.handle_flow_message(user_id, message, user_state, db_session)
        else:
            self.user_state_manager.clear_user_state(user_id)
            return "操作流程已重置，請重新開始"
        
    def _handle_parsed_message(self, user_id, parsed_data, db_session):
        """處理解析後的訊息，傳遞 db_session"""
        message_type = parsed_data.get("type")
        
        if message_type == "expense":
            return self._handle_expense(parsed_data, user_id, db_session)
        elif message_type == "income":
            return self._handle_income(parsed_data, user_id, db_session)
        elif message_type == "query":
            return self._handle_query(user_id, db_session)
        elif message_type == "asset_query":
            return self._handle_asset_query(user_id, db_session)
        elif message_type == "goal_query":
            return self._handle_goal_query(user_id, db_session)
        elif message_type == "manage_goal":
            return self._handle_manage_goal(user_id, db_session)
        elif message_type == "goal_progress":
            return self._handle_goal_progress(user_id, db_session)
        
        # 啟動流程的指令現在也需要傳遞 db_session
        elif message_type.startswith("start_"):
            flow_type = message_type.replace("start_", "") + "_flow"
            handler = self.flow_handlers.get(flow_type)
            if handler:
                # 為了統一架構，所有 start_flow 都接收 db_session，即使它可能不會使用
                return handler.start_flow(user_id, db_session)
        
        return self._get_help_message()
        
    def _handle_expense(self, parsed_data, user_id, db_session):
        """處理支出記錄並更新資產餘額"""
        try:
            budget_manager = BudgetManager()
            asset_manager = AssetManager()

            # 1. 新增交易紀錄
            budget_manager.add_transaction(
                db_session, user_id, datetime.now().strftime("%Y-%m-%d"),
                parsed_data['category'], parsed_data['amount'], 'expense',
                parsed_data['budget_category'], parsed_data.get('description', '')
            )

            # 2. 處理資產餘額更新
            asset_update_msg = ""
            target_asset_name = parsed_data.get("target_asset")
            if target_asset_name:
                asset = asset_manager.find_asset_by_name(db_session, user_id, target_asset_name)
                if asset:
                    amount_change = -float(parsed_data["amount"])
                    asset_manager.adjust_asset_balance(db_session, user_id, asset['account_key'], amount_change)
                    asset_update_msg = f"\n已從 {asset['bank_name']} 扣款。"
                else:
                    asset_update_msg = f"\n⚠️ 但找不到名為 {target_asset_name} 的資產。"
            
            original_text = f"✅ 支出 {parsed_data['amount']}元 紀錄成功！"
            return original_text + asset_update_msg
        except Exception as e:
            return self.response_builder.create_error_message(f"紀錄失敗: {e}")

    def _handle_income(self, parsed_data, user_id, db_session):
        """處理收入記錄並更新資產餘額"""
        try:
            budget_manager = BudgetManager()
            asset_manager = AssetManager()

            # 1. 新增交易紀錄
            budget_manager.add_transaction(
                db_session, user_id, datetime.now().strftime("%Y-%m-%d"),
                parsed_data['category'], parsed_data['amount'], 'income',
                parsed_data['budget_category'], parsed_data.get('description', '')
            )

            # 2. 處理資產餘額更新
            asset_update_msg = ""
            target_asset_name = parsed_data.get("target_asset")
            if target_asset_name:
                asset = asset_manager.find_asset_by_name(db_session, user_id, target_asset_name)
                if asset:
                    amount_change = float(parsed_data["amount"])
                    asset_manager.adjust_asset_balance(db_session, user_id, asset['account_key'], amount_change)
                    asset_update_msg = f"\n已存入 {asset['bank_name']}。"
                else:
                    asset_update_msg = f"\n⚠️ 但找不到名為 {target_asset_name} 的資產。"

            original_text = f"✅ 收入 {parsed_data['amount']}元 紀錄成功！"
            return original_text + asset_update_msg
        except Exception as e:
            return self.response_builder.create_error_message(f"紀錄失敗: {e}")
    
    def _handle_query(self, user_id, db_session):
        """處理查詢請求"""
        try:
            budget_manager = BudgetManager()
            month = datetime.now().strftime("%Y-%m")
            total_expenses = sum(budget_manager.calculate_monthly_expenses(db_session, user_id, month).values())
            transactions = budget_manager.get_all_transactions(db_session, user_id)
            
            # 簡單重構查詢邏輯
            recent_transactions = [t for t in transactions if t['date'].startswith(month)][:5]
            transaction_count = len([t for t in transactions if t['date'].startswith(month)])
            
            return self.response_builder.create_monthly_summary(
                month, total_expenses, transaction_count, recent_transactions, {}
            )
        except Exception as e:
            return self.response_builder.create_error_message(f"查詢失敗: {e}")
    
    def _handle_asset_query(self, user_id, db_session):
        """處理資產查詢"""
        try:
            totals = AssetManager().calculate_totals(db_session, user_id)
            return self.response_builder.create_asset_overview(totals)
        except Exception as e:
            return self.response_builder.create_error_message(f"查詢資產失敗: {e}")
    
    def _handle_goal_query(self, user_id, db_session):
        """處理目標查詢"""
        try:
            goal_manager = GoalManager()
            goals = goal_manager.get_all_goals(db_session, user_id)
            summary = goal_manager.calculate_goal_summary(db_session, user_id)
            return self.response_builder.create_goal_overview(goals, summary)
        except Exception as e:
            return self.response_builder.create_error_message(f"查詢目標失敗: {e}")
        
    def _handle_manage_goal(self, user_id, db_session):
        """處理管理目標"""
        try:
            goals = GoalManager().get_all_goals(db_session, user_id)
            return self.response_builder.create_goal_management(goals)
        except Exception as e:
            return self.response_builder.create_error_message(f"查詢目標失敗: {e}")

    def _handle_goal_progress(self, user_id, db_session):
        """處理目標進度查詢"""
        try:
            goals = GoalManager().get_all_goals(db_session, user_id)
            return self.response_builder.create_goal_progress(goals)
        except Exception as e:
            return self.response_builder.create_error_message(f"查詢目標進度失敗: {e}")
    
    def _get_help_message(self):
        """取得幫助訊息"""
        return self.response_builder.create_help_message()
