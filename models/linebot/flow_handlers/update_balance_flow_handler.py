from ...asset_manager import AssetManager

class UpdateBalanceFlowHandler:
    """更新帳戶餘額流程處理器"""
    
    def __init__(self, user_state_manager, operation_theme):
        self.user_state_manager = user_state_manager
        self.theme = operation_theme
    
    def start_flow(self, user_id, db_session):
        """開始更新餘額流程"""
        assets = AssetManager().get_all_assets(db_session, user_id)
        if not assets:
            return "您還沒有任何帳戶，請先新增帳戶"
        
        self.user_state_manager.set_user_state(
            user_id, 'update_balance_flow', 'select_account'
        )
        return self.theme.create_update_balance_account_selection(list(assets.values()))
    
    def handle_flow_message(self, user_id, message, current_state, db_session):
        """處理更新餘額流程中的訊息"""
        step = current_state['step']
        
        if step == 'select_account':
            return self._handle_account_selection(user_id, message, db_session)
        elif step == 'input_balance':
            return self._handle_balance_input(user_id, message, current_state)
        elif step == 'confirm':
            return self._handle_confirmation(user_id, message, current_state, db_session)
        else:
            self.user_state_manager.clear_user_state(user_id)
            return "更新餘額流程異常，已重置。"
    
    def _handle_account_selection(self, user_id, message, db_session):
        """處理帳戶選擇"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "更新餘額已取消"
        
        account_key = message.replace("選擇帳戶:", "")
        
        assets = AssetManager().get_all_assets(db_session, user_id)
        selected_asset = assets.get(account_key)
        if not selected_asset:
            return "選擇的帳戶不存在，請重新選擇"
        
        self.user_state_manager.update_user_state(
            user_id,
            step='input_balance',
            data={'account_key': account_key, 'selected_asset': selected_asset}
        )
        return self.theme.create_balance_input(selected_asset)
    
    def _handle_balance_input(self, user_id, message, current_state):
        """處理餘額輸入"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "更新餘額已取消"
        
        try:
            new_balance = float(message.replace(',', ''))
            if new_balance < 0:
                return self.theme.create_balance_input(
                    current_state['data']['selected_asset'], 
                    error_message="餘額不能為負數，請重新輸入"
                )
            
            updated_data = {**current_state['data'], 'new_balance': new_balance}
            self.user_state_manager.update_user_state(
                user_id, step='confirm', data=updated_data
            )
            return self.theme.create_update_confirmation(updated_data, new_balance)
        except ValueError:
            return self.theme.create_balance_input(
                current_state['data']['selected_asset'],
                error_message="請輸入有效的數字金額"
            )
    
    def _handle_confirmation(self, user_id, message, current_state, db_session):
        """處理確認更新"""
        if message == "確認更新":
            data = current_state['data']
            
            AssetManager().update_balance(
                db_session, user_id, data['account_key'], data['new_balance']
            )
            
            self.user_state_manager.clear_user_state(user_id)
            return self.theme.create_update_success(data)
        
        elif message == "取消更新":
            self.user_state_manager.clear_user_state(user_id)
            return "更新餘額已取消"
        else:
            return "請點擊「確認更新」或「取消更新」"