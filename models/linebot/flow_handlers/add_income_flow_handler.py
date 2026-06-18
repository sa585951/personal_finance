from datetime import datetime
from ...budget_manager import BudgetManager

class AddIncomeFlowHandler:
    """新增收入流程處理器"""

    def __init__(self, user_state_manager, operation_theme, budget_manager, asset_manager):
        self.user_state_manager = user_state_manager
        self.theme = operation_theme
        self.budget_manager = budget_manager
        self.asset_manager = asset_manager
        self.income_categories = ["薪資", "獎金", "利息", "其他"]

    def start_flow(self, user_id):
        """開始新增收入流程"""
        self.user_state_manager.set_user_state(
            user_id, 'add_income_flow', 'select_category'
        )
        return self.theme.create_category_selection(self.income_categories, "income")

    def handle_flow_message(self, user_id, message, current_state):
        """處理流程中的訊息"""
        step = current_state.get('step')
        
        if step == 'select_category':
            return self._handle_category_selection(user_id, message)
        elif step == 'input_amount':
            return self._handle_amount_input(user_id, message, current_state)
        elif step == 'input_description':
            return self._handle_description_input(user_id, message, current_state)
        elif step == 'confirm':
            return self._handle_confirmation(user_id, message, current_state)
        else:
            self.user_state_manager.clear_user_state(user_id)
            return "流程異常，已重置。請重新開始。"

    def _handle_category_selection(self, user_id, message):
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "新增收入已取消"

        category = message.replace("選擇類別:", "").strip()
        
        if category not in self.income_categories:
            return self.theme.create_category_selection(self.income_categories, "income", "請選擇有效的收入類別")

        self.user_state_manager.update_user_state(
            user_id,
            step='input_amount',
            data={'category': category}
        )
        return self.theme.create_amount_input("收入")

    def _handle_amount_input(self, user_id, message, current_state):
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "新增收入已取消"
        
        try:
            amount = float(message.replace(',', ''))
            if amount <= 0:
                return self.theme.create_amount_input("收入", "金額必須大於0，請重新輸入")
            
            self.user_state_manager.update_user_state(
                user_id,
                step='input_description',
                data={'amount': amount}
            )
            return self.theme.create_description_input()
            
        except ValueError:
            return self.theme.create_amount_input("收入", "請輸入有效的數字金額")

    def _handle_description_input(self, user_id, message, current_state):
        if message.lower() == "取消":
            self.user_state_manager.clear_user_state(user_id)
            return "新增收入已取消"

        description = ""
        if message.lower() != "跳過":
            description = message.strip()

        self.user_state_manager.update_user_state(
            user_id,
            step='confirm',
            data={'description': description}
        )
        
        confirm_data = current_state['data']
        confirm_data['description'] = description
        return self.theme.create_transaction_confirmation("收入", confirm_data)

    def _handle_confirmation(self, user_id, message, current_state):
        """處理最終確認"""
        if message == "確認新增":
            data = current_state['data']
            
            self.budget_manager.add_transaction(
                user_id=user_id,
                date=datetime.now().strftime("%Y-%m-%d"),
                item=data["category"],
                amount=data["amount"],
                transaction_type="income",
                budget_category=data["category"],
                description=data["description"]
            )

            self.user_state_manager.clear_user_state(user_id)
            return self.theme.create_add_transaction_success("收入", data)

        elif message == "取消新增":
            self.user_state_manager.clear_user_state(user_id)
            return "新增收入已取消"
        else:
            return "請點擊「確認新增」或「取消新增」"
