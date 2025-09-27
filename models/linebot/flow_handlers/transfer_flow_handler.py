from ...asset_manager import AssetManager

class TransferFlowHandler:
    """處理帳戶間轉帳的流程"""
    
    def __init__(self, user_state_manager, operation_theme):
        self.user_state_manager = user_state_manager
        self.theme = operation_theme
    
    # start_flow 現在需要 db_session
    def start_flow(self, user_id, db_session):
        """開始轉帳流程"""
        assets = AssetManager().get_all_assets(db_session, user_id)
        
        if len(assets) < 2:
            return "您需要至少兩個帳戶才能進行轉帳\n請先新增更多帳戶"
        
        self.user_state_manager.set_user_state(user_id, 'transfer_flow', 'select_source')
        return self.theme.create_transfer_account_selection(assets, "請選擇轉出帳戶", "source")
    
    # handle_flow_message 也需要 db_session
    def handle_flow_message(self, user_id, message, current_state, db_session):
        """處理轉帳流程中的訊息"""
        step = current_state['step']
        
        if step == 'select_source':
            return self._handle_source_selection(user_id, message, db_session)
        elif step == 'select_target':
            return self._handle_target_selection(user_id, message, db_session)
        elif step == 'input_amount':
            return self._handle_amount_input(user_id, message, current_state, db_session)
        elif step == 'confirm':
            return self._handle_confirmation(user_id, message, current_state, db_session)
        else:
            self.user_state_manager.clear_user_state(user_id)
            return "轉帳流程異常，已重置。請重新開始"
    
    def _handle_source_selection(self, user_id, message, db_session):
        """處理來源帳戶選擇"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "轉帳已取消"
        
        source_account_key = message.replace("選擇帳戶:", "")
        assets = AssetManager().get_all_assets(db_session, user_id)
        if source_account_key not in assets:
            return "選擇的帳戶不存在，請重新選擇"
        
        self.user_state_manager.update_user_state(
            user_id, step='select_target', data={'source_account': source_account_key}
        )
        
        target_assets = {k: v for k, v in assets.items() if k != source_account_key}
        return self.theme.create_transfer_account_selection(target_assets, "請選擇轉入帳戶", "target")
    
    def _handle_target_selection(self, user_id, message, db_session):
        """處理目標帳戶選擇"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "轉帳已取消"

        target_account_key = message.replace("選擇帳戶:", "")
        current_state = self.user_state_manager.get_user_state(user_id)
        source_key = current_state['data']['source_account']
        
        assets = AssetManager().get_all_assets(db_session, user_id)
        source_account = assets.get(source_key)
        target_account = assets.get(target_account_key)

        if not source_account or not target_account:
            self.user_state_manager.clear_user_state(user_id)
            return "發生錯誤：找不到帳戶資訊，流程已重置。"

        self.user_state_manager.update_user_state(
            user_id, step='input_amount', data={'target_account': target_account_key}
        )
        return self.theme.create_transfer_amount_input(source_account, target_account)
    
    def _handle_amount_input(self, user_id, message, current_state, db_session):
        """處理金額輸入"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "轉帳已取消"
        
        try:
            amount = float(message.replace(',', ''))
            if amount <= 0: return "金額必須大於 0，請重新輸入"
            
            data = current_state['data']
            assets = AssetManager().get_all_assets(db_session, user_id)
            source_account = assets.get(data['source_account'])

            if not source_account:
                self.user_state_manager.clear_user_state(user_id)
                return "發生錯誤：找不到來源帳戶資訊，流程已重置。"

            if amount > source_account['balance']:
                return f"金額超過帳戶餘額 ${source_account['balance']:,.0f}，請重新輸入"
            
            self.user_state_manager.update_user_state(user_id, step='confirm', data={'amount': amount})
            
            target_account = assets.get(data['target_account'])
            return self.theme.create_transfer_confirmation(source_account, target_account, amount)
        except ValueError:
            return "請輸入有效的數字金額"
    
    def _handle_confirmation(self, user_id, message, current_state, db_session):
        """處理確認轉帳"""
        if message == "確認轉帳":
            data = current_state['data']
            asset_manager = AssetManager()
            
            # 執行轉帳
            asset_manager.transfer(
                db_session, user_id, data["source_account"], data["target_account"], data["amount"]
            )
            self.user_state_manager.clear_user_state(user_id)
            
            # 獲取更新後的帳戶資訊以顯示
            updated_assets = asset_manager.get_all_assets(db_session, user_id)
            source_account = updated_assets.get(data['source_account'])
            target_account = updated_assets.get(data['target_account'])
            
            if source_account and target_account:
                return self.theme.create_transfer_success(source_account, target_account, data['amount'])
            else:
                return "轉帳成功，但顯示結果時發生錯誤。"
        
        elif message == "取消轉帳":
            self.user_state_manager.clear_user_state(user_id)
            return "轉帳已取消"
        else:
            return "請點擊「確認轉帳」或「取消轉帳」"