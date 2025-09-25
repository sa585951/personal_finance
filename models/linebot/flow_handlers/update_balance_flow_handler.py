from datetime import datetime
from linebot.models import FlexSendMessage

class UpdateBalanceFlowHandler:
    """更新帳戶餘額流程處理器"""
    
    def __init__(self, asset_manager, user_state_manager, operation_theme):
        self.asset_manager = asset_manager
        self.user_state_manager = user_state_manager
        self.theme = operation_theme
    
    def start_flow(self, user_id):
        """開始更新餘額流程"""
        try:
            # 獲取所有帳戶
            assets = self.asset_manager.get_all_assets(user_id)
            if not assets:
                return "您還沒有任何帳戶，請先新增帳戶"
            
            # 設定用戶狀態
            self.user_state_manager.set_user_state(
                user_id, 'update_balance_flow', 'select_account'
            )
            
            return self.theme.create_update_balance_account_selection(list(assets.values()))
            
        except Exception as e:
            return f"更新餘額流程啟動失敗: {str(e)}"
    
    def handle_flow_message(self, user_id, message, current_state):
        """處理更新餘額流程中的訊息"""
        step = current_state['step']
        
        if step == 'select_account':
            return self._handle_account_selection(user_id, message)
        elif step == 'input_balance':
            return self._handle_balance_input(user_id, message, current_state)
        elif step == 'confirm':
            return self._handle_confirmation(user_id, message, current_state)
        else:
            self.user_state_manager.clear_user_state(user_id)
            return "更新餘額流程異常，已重置。請重新開始"
    
    
    def _handle_account_selection(self, user_id, message):
        """處理帳戶選擇"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "更新餘額已取消"
        
        if not message.startswith("選擇帳戶:"):
            return "請點擊按鈕選擇帳戶，或輸入「取消操作」"
        
        account_key = message.replace("選擇帳戶:", "")
        
        # 驗證帳戶是否存在
        assets = self.asset_manager.get_all_assets(user_id)
        selected_asset = assets.get(account_key)
        if not selected_asset:
            return "選擇的帳戶不存在，請重新選擇"
        
        # 更新狀態
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
                selected_asset = current_state['data']['selected_asset']
                return self.theme.create_balance_input(
                    selected_asset, 
                    error_message="餘額不能為負數，請重新輸入"
                )
            
            # 將新餘額合併到現有資料中，而不是覆蓋
            updated_data = current_state['data'].copy()
            updated_data['new_balance'] = new_balance

            # 更新狀態
            self.user_state_manager.update_user_state(
                user_id,
                step='confirm',
                data=updated_data
            )
            
            return self.theme.create_update_confirmation(updated_data, new_balance)
            
        except ValueError:
            selected_asset = current_state['data']['selected_asset']
            return self.theme.create_balance_input(
                selected_asset,
                error_message="請輸入有效的數字金額"
            )
    
    def _handle_confirmation(self, user_id, message, current_state):
        """處理確認更新"""
        if message == "確認更新":
            # 執行餘額更新
            data = current_state['data']
            success, result_message = self.asset_manager.update_balance(
                user_id,
                data['account_key'],
                data['new_balance']
            )
            
            # 清除狀態
            self.user_state_manager.clear_user_state(user_id)
            
            if success:
                return self.theme.create_update_success(data)
            else:
                return f"更新餘額失敗: {result_message}"
        
        elif message == "取消更新":
            self.user_state_manager.clear_user_state(user_id)
            return "更新餘額已取消"
        else:
            return "請點擊「確認更新」或「取消更新」"
    