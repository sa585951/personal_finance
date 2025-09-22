class DeleteAssetFlowHandler:
    """刪除資產流程處理器"""
    
    def __init__(self, asset_manager, user_state_manager, operation_theme):
        self.asset_manager = asset_manager
        self.user_state_manager = user_state_manager
        self.theme = operation_theme
    
    def start_flow(self, user_id):
        """開始刪除資產流程"""
        try:
            # 獲取所有帳戶
            assets = self.asset_manager.get_all_assets(user_id)
            if not assets:
                return "您還沒有任何帳戶，無法執行刪除操作"
            
            # 設定用戶狀態
            self.user_state_manager.set_user_state(
                user_id, 'delete_asset_flow', 'select_account'
            )
            
            return self.theme.create_delete_asset_account_selection(list(assets.values()))
            
        except Exception as e:
            return f"刪除資產流程啟動失敗: {str(e)}"
    
    def handle_flow_message(self, user_id, message, current_state):
        """處理刪除資產流程中的訊息"""
        step = current_state['step']
        
        if step == 'select_account':
            return self._handle_account_selection(user_id, message)
        elif step == 'confirm':
            return self._handle_confirmation(user_id, message, current_state)
        else:
            self.user_state_manager.clear_user_state(user_id)
            return "刪除資產流程異常，已重置。請重新開始"
    
    def _handle_account_selection(self, user_id, message):
        """處理帳戶選擇"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "刪除資產已取消"
        
        if not message.startswith("刪除帳戶:"):
            return "請點擊按鈕選擇要刪除的帳戶，或輸入「取消操作」"
        
        account_key = message.replace("刪除帳戶:", "")
        
        # 驗證帳戶是否存在
        assets = self.asset_manager.get_all_assets(user_id)
        selected_asset = assets.get(account_key)        
        
        if not selected_asset:
            return "選擇的帳戶不存在，請重新選擇"
        
        # 檢查帳戶餘額
        if selected_asset['balance'] > 0:
            self.user_state_manager.clear_user_state(user_id)
            return f"無法刪除帳戶：{selected_asset['bank_name']} {selected_asset['account_type']} 仍有餘額 ${selected_asset['balance']:,.0f}，請先轉移資金或將餘額歸零"
        
        # 更新狀態到確認步驟
        self.user_state_manager.update_user_state(
            user_id,
            step='confirm',
            data={'account_key': account_key, 'selected_asset': selected_asset}
        )
        
        return self.theme.create_delete_asset_confirmation(selected_asset)
    
    def _handle_confirmation(self, user_id, message, current_state):
        """處理確認刪除"""
        if message == "確認刪除":
            # 執行刪除操作
            data = current_state['data']
            account_key = data['account_key']
            success, msg = self.asset_manager.delete_account(user_id, account_key)

            # 清除狀態
            self.user_state_manager.clear_user_state(user_id)

            if success:
                return self.theme.create_delete_asset_success(data['selected_asset'])
            else:
                return f"刪除帳戶失敗: {msg}"

        elif message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "刪除資產已取消"
        else:
            return "請點擊「確認刪除」或「取消刪除」"