class AddAccountFlowHandler:
    """新增帳戶流程處理器"""
    
    def __init__(self, asset_manager, user_state_manager, operation_theme):
        self.asset_manager = asset_manager
        self.user_state_manager = user_state_manager
        self.theme = operation_theme
        
        # 帳戶類型選項
        self.account_types = ["活存", "定存", "投資", "信用卡", "其他"]
    
    def start_flow(self, user_id):
        """開始新增帳戶流程"""
        try:
            # 設定用戶狀態
            self.user_state_manager.set_user_state(
                user_id, 'add_account_flow', 'input_bank_name'
            )
            
            return self.theme.create_bank_name_input()
            
        except Exception as e:
            return f"新增帳戶流程啟動失敗: {str(e)}"
            
    def handle_flow_message(self, user_id, message, current_state):
        """處理新增帳戶流程中的訊息"""
        step = current_state['step']
        
        if step == 'input_bank_name':
            return self._handle_bank_name_input(user_id, message)
        elif step == 'select_account_type':
            return self._handle_account_type_selection(user_id, message, current_state)
        elif step == 'input_balance':
            return self._handle_balance_input(user_id, message, current_state)
        elif step == 'confirm':
            return self._handle_confirmation(user_id, message, current_state)
        else:
            # 未知步驟，重置流程
            self.user_state_manager.clear_user_state(user_id)
            return "新增帳戶流程異常，已重置。請重新開始"
    
    def _handle_bank_name_input(self, user_id, message):
        """處理銀行名稱輸入"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "新增帳戶已取消"
        
        # 簡單驗證銀行名稱
        bank_name = message.strip()
        if len(bank_name) < 2:
            return self.theme.create_bank_name_input("請輸入有效的銀行名稱 (至少2個字)")
        
        if len(bank_name) > 20:
            return self.theme.create_bank_name_input("銀行名稱太長，請重新輸入")
        
        # 更新狀態到下一步
        self.user_state_manager.update_user_state(
            user_id,
            step='select_account_type',
            data={'bank_name': bank_name}
        )
        
        return self.theme.create_account_type_selection_flex(self.account_types)
    
    def _handle_account_type_selection(self, user_id, message, current_state):
        """處理帳戶類型選擇"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "新增帳戶已取消"
        
        if not message.startswith("選擇類型:"):
            return "請點擊按鈕選擇帳戶類型，或輸入「取消操作」"
        
        account_type = message.replace("選擇類型:", "")
        
        if account_type not in self.account_types:
            return "請選擇有效的帳戶類型"
        
        # 更新狀態
        self.user_state_manager.update_user_state(
            user_id,
            step='input_balance',
            data={'account_type': account_type}
        )
        
        return self.theme.create_balance_input_flex()
    
    def _handle_balance_input(self, user_id, message, current_state):
        """處理餘額輸入"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "新增帳戶已取消"
        
        try:
            balance = float(message.replace(',', ''))
            if balance < 0:
                return self.theme.create_balance_input_flex(error_message="餘額不能為負數，請重新輸入")
            
            # 更新狀態
            self.user_state_manager.update_user_state(
                user_id,
                step='confirm',
                data={'balance': balance}
            )
            
            return self.theme.create_add_account_confirmation(current_state['data'], balance)
            
        except ValueError:
            return self.theme.create_balance_input_flex(error_message="請輸入有效的數字金額")
        
    def _handle_confirmation(self, user_id, message, current_state):
        """處理確認新增"""
        if message == "確認新增":
            # 執行新增帳戶
            data = current_state['data']
            success, msg = self.asset_manager.add_account(
                user_id,
                data["bank_name"],
                data["account_type"],
                data["balance"]
            )

            # 清除狀態
            self.user_state_manager.clear_user_state(user_id)

            if success:
                return self.theme.create_add_account_success_flex(data)
            else:
                return f"新增帳戶失敗: {msg}"

        elif message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "新增帳戶已取消"
        else:
            return "請點擊「確認新增」或「取消新增」"
    