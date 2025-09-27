from ...asset_manager import AssetManager

class DeleteAssetFlowHandler:
    """刪除資產流程處理器"""
    
    def __init__(self, user_state_manager, operation_theme):
        self.user_state_manager = user_state_manager
        self.theme = operation_theme
    
    def start_flow(self, user_id, db_session):
        """開始刪除資產流程"""
        assets = AssetManager().get_all_assets(db_session, user_id)
        if not assets:
            return "您還沒有任何帳戶，無法執行刪除操作"
        
        self.user_state_manager.set_user_state(
            user_id, 'delete_asset_flow', 'select_account'
        )
        
        return self.theme.create_delete_asset_account_selection(list(assets.values()))
            
    def handle_flow_message(self, user_id, message, current_state, db_session):
        """處理刪除資產流程中的訊息"""
        step = current_state['step']
        
        if step == 'select_account':
            return self._handle_account_selection(user_id, message, db_session)
        elif step == 'confirm':
            return self._handle_confirmation(user_id, message, current_state, db_session)
        else:
            self.user_state_manager.clear_user_state(user_id)
            return "刪除資產流程異常，已重置。"
    
    def _handle_account_selection(self, user_id, message, db_session):
        """處理帳戶選擇"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "刪除資產已取消"
        
        account_key = message.replace("刪除帳戶:", "")
        
        assets = AssetManager().get_all_assets(db_session, user_id)
        selected_asset = assets.get(account_key)        
        
        if not selected_asset:
            return "選擇的帳戶不存在，請重新選擇"
        
        if selected_asset['balance'] > 0:
            self.user_state_manager.clear_user_state(user_id)
            return f"無法刪除帳戶：{selected_asset['bank_name']} {selected_asset['account_type']} 仍有餘額 ${selected_asset['balance']:,.0f}，請先轉移資金或將餘額歸零"
        
        self.user_state_manager.update_user_state(
            user_id,
            step='confirm',
            data={'account_key': account_key, 'selected_asset': selected_asset}
        )
        return self.theme.create_delete_asset_confirmation(selected_asset)
    
    def _handle_confirmation(self, user_id, message, current_state, db_session):
        """處理確認刪除"""
        if message == "確認刪除":
            data = current_state['data']
            account_key = data['account_key']
            
            AssetManager().delete_account(db_session, user_id, account_key)

            self.user_state_manager.clear_user_state(user_id)
            return self.theme.create_delete_asset_success(data['selected_asset'])

        elif message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "刪除資產已取消"
        else:
            return "請點擊「確認刪除」或「取消刪除」"