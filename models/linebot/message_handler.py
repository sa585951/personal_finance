from .handlers import ExpenseHandler, IncomeHandler, QueryHandler, AssetHandler, GoalHandler
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
    def __init__(self, budget_manager, asset_manager, goal_manager, user_state_manager):
        self.budget_manager = budget_manager
        self.asset_manager = asset_manager
        self.user_state_manager = user_state_manager
        self.goal_manager = goal_manager

        # 初始化各種 handlers
        self.expense_handler = ExpenseHandler(budget_manager)
        self.income_handler = IncomeHandler(budget_manager)
        self.query_handler = QueryHandler(budget_manager)
        self.asset_handler = AssetHandler(asset_manager)
        self.goal_handler = GoalHandler(goal_manager)
        self.response_builder = ResponseBuilder()
        operation_theme = self.response_builder.operation_theme

        #初始化流程處理器
        self.transfer_flow_handler = TransferFlowHandler(asset_manager, self.user_state_manager, operation_theme)
        self.add_account_flow_handler = AddAccountFlowHandler(asset_manager, self.user_state_manager, operation_theme)
        self.update_balance_flow_handler = UpdateBalanceFlowHandler(asset_manager, self.user_state_manager, operation_theme)
        self.delete_asset_flow_handler = DeleteAssetFlowHandler(asset_manager, self.user_state_manager, operation_theme)
        self.delete_transaction_flow_handler = DeleteTransactionFlowHandler(budget_manager, self.user_state_manager, operation_theme)
        self.add_goal_flow_handler = AddGoalFlowHandler(goal_manager, self.user_state_manager, operation_theme)
        self.add_expense_flow_handler = AddExpenseFlowHandler(budget_manager, self.user_state_manager, operation_theme)
        self.add_income_flow_handler = AddIncomeFlowHandler(budget_manager, self.user_state_manager, operation_theme)
        self.edit_goal_flow_handler = EditGoalFlowHandler(goal_manager, self.user_state_manager, operation_theme)
        self.delete_goal_flow_handler = DeleteGoalFlowHandler(goal_manager, self.user_state_manager, operation_theme)

    def handle_user_message(self, user_id, message, parsed_data):
        """處理用戶訊息的主要入口"""
        # 檢查是否在流程中
        user_state = self.user_state_manager.get_user_state(user_id)
        if user_state:
            return self._handle_flow_message(user_id, message, user_state)
        
        # 根據解析結果處理訊息
        return self._handle_parsed_message(user_id, parsed_data)
    
    def _handle_flow_message(self, user_id, message, user_state):
        """處理流程中的訊息"""
        state_type = user_state["type"]
        
        if state_type == "transfer_flow":
            return self.transfer_flow_handler.handle_flow_message(user_id, message, user_state)
        elif state_type == "add_account_flow":
            return self.add_account_flow_handler.handle_flow_message(user_id, message, user_state)
        elif state_type == "update_balance_flow":
            return self.update_balance_flow_handler.handle_flow_message(user_id, message, user_state)
        elif state_type == "delete_asset_flow":
            return self.delete_asset_flow_handler.handle_flow_message(user_id, message, user_state)
        elif state_type == "delete_transaction_flow":
            return self.delete_transaction_flow_handler.handle_flow_message(user_id, message, user_state)
        elif state_type == "add_goal_flow":
            return self.add_goal_flow_handler.handle_flow_message(user_id, message, user_state)
        elif state_type == "add_expense_flow":
            return self.add_expense_flow_handler.handle_flow_message(user_id, message, user_state)
        elif state_type == "add_income_flow":
            return self.add_income_flow_handler.handle_flow_message(user_id, message, user_state)
        elif state_type == "edit_goal_flow":
            return self.edit_goal_flow_handler.handle_flow_message(user_id, message, user_state)
        elif state_type == "delete_goal_flow":
            return self.delete_goal_flow_handler.handle_flow_message(user_id, message, user_state)
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
        elif message_type == "goal_query":
            return self._handle_goal_query(user_id)
        elif message_type == "start_transfer":
            return self.transfer_flow_handler.start_flow(user_id)
        elif message_type == "start_add_account":
            return self.add_account_flow_handler.start_flow(user_id)
        elif message_type == "start_update_balance":
            return self.update_balance_flow_handler.start_flow(user_id)
        elif message_type == "start_delete_asset":
            return self.delete_asset_flow_handler.start_flow(user_id)
        elif message_type == "start_delete_transaction":
            return self.delete_transaction_flow_handler.start_flow(user_id)
        elif message_type == "start_add_goal":
            return self.add_goal_flow_handler.start_flow(user_id)
        elif message_type == "start_add_expense":
            return self.add_expense_flow_handler.start_flow(user_id)
        elif message_type == "start_add_income":
            return self.add_income_flow_handler.start_flow(user_id)
        elif message_type == "start_edit_goal":
            return self.edit_goal_flow_handler.start_flow(user_id, parsed_data.get("goal_id"))
        elif message_type == "start_delete_goal":
            return self.delete_goal_flow_handler.start_flow(user_id, parsed_data.get("goal_id"))
        elif message_type == "manage_goal":
            return self._handle_manage_goal(user_id)
        elif message_type == "goal_progress":
            return self._handle_goal_progress(user_id)
        else:
            return self._get_help_message()
        
    def _handle_expense(self, parsed_data, user_id):
        """處理支出記錄並更新資產餘額"""
        # 1. 新增交易紀錄
        result = self.expense_handler.handle(parsed_data, user_id)
        if not result["success"]:
            return self.response_builder.create_error_message(f"紀錄失敗: {result['message']}")

        # 2. 處理資產餘額更新
        asset_update_msg = ""
        target_asset_name = parsed_data.get("target_asset")
        if target_asset_name:
            asset = self.asset_manager.find_asset_by_name(target_asset_name)
            if asset:
                amount_change = -float(parsed_data["amount"])
                self.asset_manager.adjust_asset_balance(asset['account_key'], amount_change)
                asset_update_msg = f"\n已從 {asset['bank_name']} 扣款。"
            else:
                asset_update_msg = f"\n⚠️ 但找不到名為 {target_asset_name} 的資產。"

        # 3. 建立成功回應
        base_response = self.response_builder.create_expense_success(
            result["data"], 
            result.get("budget_status")
        )
        # 將文字和 Flex Message 合併
        if isinstance(base_response, str):
            return base_response + asset_update_msg
        else: # 假設是 FlexSendMessage
            # 這裡我們簡單地在文字回覆中附加訊息
            # 注意：Flex Message 的內容是固定的，較難動態附加文字
            # 一個簡單的作法是，如果需要附加資產訊息，就改用純文字回覆
            original_text = f"✅ 支出 {parsed_data['amount']}元 紀錄成功！"
            return original_text + asset_update_msg

    def _handle_income(self, parsed_data, user_id):
        """處理收入記錄並更新資產餘額"""  
        # 1. 新增交易紀錄
        result = self.income_handler.handle(parsed_data, user_id)
        if not result["success"]:
            return self.response_builder.create_error_message(f"紀錄失敗: {result['message']}")

        # 2. 處理資產餘額更新
        asset_update_msg = ""
        target_asset_name = parsed_data.get("target_asset")
        if target_asset_name:
            asset = self.asset_manager.find_asset_by_name(target_asset_name)
            if asset:
                amount_change = float(parsed_data["amount"])
                self.asset_manager.adjust_asset_balance(asset['account_key'], amount_change)
                asset_update_msg = f"\n已存入 {asset['bank_name']}。"
            else:
                asset_update_msg = f"\n⚠️ 但找不到名為 {target_asset_name} 的資產。"

        # 3. 建立成功回應
        base_response = self.response_builder.create_income_success(result["data"])
        if isinstance(base_response, str):
            return base_response + asset_update_msg
        else:
            original_text = f"✅ 收入 {parsed_data['amount']}元 紀錄成功！"
            return original_text + asset_update_msg
    
    def _handle_query(self, user_id):
        """處理查詢請求"""
        result = self.query_handler.handle(user_id)
        if result["success"]:
            return self.response_builder.create_monthly_summary(
                result["month"],
                result["total_expenses"],
                result["transaction_count"],
                result["recent_transactions"],
                result["category_stats"]
            )
        else:
            return self.response_builder.create_error_message(f"查詢失敗: {result['message']}")
    
    def _handle_asset_query(self, user_id):
        """處理資產查詢"""
        result = self.asset_handler.handle(user_id)
        if result["success"]:
            return self.response_builder.create_asset_overview(result["totals"])
        else:
            return self.response_builder.create_error_message(result['message'])
    
    def _handle_goal_query(self, user_id):
        """處理目標查詢"""
        result = self.goal_handler.handle_goal_query(user_id)
        if result["success"]:
            return self.response_builder.create_goal_overview(result["goals"], result["summary"])
        else:
            return self.response_builder.create_error_message(result['message'])
        
    def _handle_manage_goal(self, user_id):
        """處理管理目標"""
        # 顯示目標列表供編輯/刪除
        result = self.goal_handler.handle_goal_query(user_id)
        if result["success"]:
            return self.response_builder.create_goal_management(result["goals"])
        else:
            return self.response_builder.create_error_message(result["message"])

    def _handle_goal_progress(self, user_id):
        """處理目標進度查詢"""
        result = self.goal_handler.handle_goal_query(user_id)
        if result["success"]:
            return self.response_builder.create_goal_progress(result["goals"])
        else:
            return self.response_builder.create_error_message(result["message"])
    
    def _get_help_message(self):
        """取得幫助訊息"""
        return self.response_builder.create_help_message()