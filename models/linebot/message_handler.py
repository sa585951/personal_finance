from .handlers import ExpenseHandler, IncomeHandler, QueryHandler, AssetHandler
from .flow_handlers.transfer_flow_handler import TransferFlowHandler
from .flow_handlers.add_account_flow_handler import AddAccountFlowHandler
from .flow_handlers.update_balance_flow_handler import UpdateBalanceFlowHandler
from .flow_handlers.delete_asset_flow_handler import DeleteAssetFlowHandler
from .flow_handlers.delete_transaction_flow_handler import DeleteTransactionFlowHandler
from .response_builder import ResponseBuilder

class MessageHandler:
    """訊息處理器 - 負責訊息路由和處理邏輯"""
    def __init__(self, budget_manager, asset_manager, user_state_manager):
        self.budget_manager = budget_manager
        self.asset_manager = asset_manager
        self.user_state_manager = user_state_manager

        # 初始化各種 handlers
        self.expense_handler = ExpenseHandler(budget_manager)
        self.income_handler = IncomeHandler(budget_manager)
        self.query_handler = QueryHandler(budget_manager)
        self.asset_handler = AssetHandler(asset_manager)
        self.response_builder = ResponseBuilder()
        operation_theme = self.response_builder.operation_theme

        #初始化流程處理器
        self.transfer_flow_handler = TransferFlowHandler(asset_manager, self.user_state_manager, operation_theme)
        self.add_account_flow_handler = AddAccountFlowHandler(asset_manager, self.user_state_manager, operation_theme)
        self.update_balance_flow_handler = UpdateBalanceFlowHandler(asset_manager, self.user_state_manager, operation_theme)
        self.delete_asset_flow_handler = DeleteAssetFlowHandler(asset_manager, self.user_state_manager, operation_theme)
        self.delete_transaction_flow_handler = DeleteTransactionFlowHandler(budget_manager, self.user_state_manager, operation_theme)

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
        else:
            return self._get_help_message()
        
    def _handle_expense(self, parsed_data, user_id):
        """處理支出記錄"""
        result = self.expense_handler.handle(parsed_data, user_id)
        if result["success"]:
            return self.response_builder.create_expense_success(
            result["data"], 
            result.get("budget_status")
        )
        else:
            return self.response_builder.create_error_message(f"紀錄失敗: {result['message']}")
        
    def _handle_income(self, parsed_data, user_id):
        """處理收入記錄"""  
        result = self.income_handler.handle(parsed_data, user_id)
        if result["success"]:
            return self.response_builder.create_income_success(result["data"])
        else:
            return self.response_builder.create_error_message(f"紀錄失敗: {result['message']}")
    
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
            return self.response_builder.create_error_message(f"查詢失敗: {result['message']}")
    
    def _get_help_message(self):
        """取得幫助訊息"""
        return self.response_builder.create_help_message()
