from datetime import datetime


class SetBudgetFlowHandler:
    """
    設定預算流程處理器
    流程:
    1. 詢問月份 (預設本月/下個月)
    2. 詢問類別 (顯示所有預算類別)
    3. 詢問金額
    4. 確認並儲存
    """
    def __init__(self, user_state_manager, operation_theme, budget_manager):
        self.user_state_manager = user_state_manager
        self.operation_theme = operation_theme
        self.budget_manager = budget_manager
        self.categories = ["伙食", "交通", "購物", "娛樂", "醫療", "工作", "生活", "其他"]

    def start_flow(self, user_id):
        """啟動流程"""
        self.user_state_manager.set_user_state(user_id, "set_budget_flow", step=1, data={})
        
        # 使用新的日期選擇器介面
        return self.operation_theme.create_month_selection_message("請問要設定哪一個月份的預算？")

    def handle_flow_message(self, user_id, message, user_state):
        # 處理取消指令
        if message in ["取消", "取消操作"]:
            self.user_state_manager.clear_user_state(user_id)
            return "已取消設定預算。"

        step = user_state.get("step")
        data = user_state.get("data", {})

        if step == 1:
            return self._handle_step_1_month(user_id, message, data)
        elif step == 2:
            return self._handle_step_2_category(user_id, message, data)
        elif step == 3:
            return self._handle_step_3_amount(user_id, message, data)
        
        return "發生錯誤，請重新開始。"

    def _handle_step_1_month(self, user_id, message, data):
        # 處理 DatetimePicker 回傳的日期 (格式 YYYY-MM-DD)
        # 我們只需要 YYYY-MM
        try:
            # 嘗試解析日期
            date_obj = datetime.strptime(message, "%Y-%m-%d")
            month_str = date_obj.strftime("%Y-%m")
        except ValueError:
            # 如果不是完整日期，嘗試解析 YYYY-MM
            import re
            if re.match(r"^\d{4}-\d{2}$", message):
                month_str = message
            else:
                return "日期格式不正確，請使用按鈕選擇或輸入 YYYY-MM"
        
        data['month'] = month_str
        self.user_state_manager.update_user_state(user_id, step=2, data=data)
        
        return self.operation_theme.create_budget_category_selection(data['month'], self.categories)

    def _handle_step_2_category(self, user_id, message, data):
        if message not in self.categories:
            return self.operation_theme.create_budget_category_selection(
                data['month'],
                self.categories,
                "請選擇有效的預算類別",
            )

        data['category'] = message
        self.user_state_manager.update_user_state(user_id, step=3, data=data)

        return self.operation_theme.create_budget_amount_input(data['month'], data['category'])

    def _handle_step_3_amount(self, user_id, message, data):
        try:
            amount = float(message)
            if amount < 0:
                return self.operation_theme.create_budget_amount_input(
                    data['month'],
                    data['category'],
                    "金額不能為負數，請重新輸入。",
                )
            
            # 儲存預算
            success, result_msg = self.budget_manager.set_budget(
                user_id, data['month'], data['category'], amount
            )
            
            self.user_state_manager.clear_user_state(user_id)
            
            if success:
                return f"✅ 預算設定成功！\n\n月份: {data['month']}\n類別: {data['category']}\n金額: {amount}"
            else:
                return f"❌ 設定失敗: {result_msg}"
                
        except ValueError:
            return self.operation_theme.create_budget_amount_input(
                data['month'],
                data['category'],
                "請輸入有效的數字金額。",
            )
