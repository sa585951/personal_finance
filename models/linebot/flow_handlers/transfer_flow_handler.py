from datetime import datetime
from linebot.models import FlexSendMessage

class TransferFlowHandler:
    """轉帳流程處理器"""
    
    def __init__(self, asset_manager, user_state_manager, operation_theme):
        self.asset_manager = asset_manager
        self.user_state_manager = user_state_manager
        self.theme = operation_theme
    
    def start_flow(self, user_id):
        """開始轉帳流程"""
        try:
            # 獲取所有帳戶
            assets = self.asset_manager.get_all_assets()
            
            if len(assets) < 2:
                return "您需要至少兩個帳戶才能進行轉帳\n請先新增更多帳戶"
            
            # 設定用戶狀態
            self.user_state_manager.set_user_state(
                user_id, 'transfer_flow', 'select_source'
            )
            
            return self.theme.create_transfer_account_selection(
                assets, "請選擇轉出帳戶", "source"
            )
            
        except Exception as e:
            return f"轉帳流程啟動失敗: {str(e)}"
    
    def handle_flow_message(self, user_id, message, current_state):
        """處理轉帳流程中的訊息"""
        step = current_state['step']
        
        if step == 'select_source':
            return self._handle_source_selection(user_id, message)
        elif step == 'select_target':
            return self._handle_target_selection(user_id, message)
        elif step == 'input_amount':
            return self._handle_amount_input(user_id, message, current_state)
        elif step == 'confirm':
            return self._handle_confirmation(user_id, message, current_state)
        else:
            # 未知步驟，重置流程
            self.user_state_manager.clear_user_state(user_id)
            return "轉帳流程異常，已重置。請重新開始"
    
    def _handle_source_selection(self, user_id, message):
        """處理來源帳戶選擇"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "轉帳已取消"
        
        if not message.startswith("選擇帳戶:"):
            return "請點擊按鈕選擇帳戶，或輸入「取消操作」"
        
        source_account_key = message.replace("選擇帳戶:", "")
        
        # 驗證帳戶存在
        assets = self.asset_manager.get_all_assets()
        if source_account_key not in assets:
            return "選擇的帳戶不存在，請重新選擇"
        
        # 更新狀態到下一步
        self.user_state_manager.update_user_state(
            user_id, 
            step='select_target',
            data={'source_account': source_account_key}
        )
        
        # 過濾掉來源帳戶，顯示目標帳戶選擇
        target_assets = {k: v for k, v in assets.items() if k != source_account_key}
        
        return self.theme.create_transfer_account_selection(
            target_assets, "請選擇轉入帳戶", "target"
        )
    
    def _handle_target_selection(self, user_id, message):
        """處理目標帳戶選擇"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "轉帳已取消"
        
        if not message.startswith("選擇帳戶:"):
            return "請點擊按鈕選擇帳戶，或輸入「取消操作」"
        
        target_account_key = message.replace("選擇帳戶:", "")
        
        # 獲取完整帳戶資訊
        current_state = self.user_state_manager.get_user_state(user_id)
        source_key = current_state['data']['source_account']
        assets = self.asset_manager.get_all_assets()
        source_account = assets.get(source_key)
        target_account = assets.get(target_account_key)

        if not source_account or not target_account:
            self.user_state_manager.clear_user_state(user_id)
            return "發生錯誤：找不到帳戶資訊，流程已重置。"

        # 更新狀態
        self.user_state_manager.update_user_state(
            user_id,
            step='input_amount',
            data={'target_account': target_account_key}
        )
        
        # 呼叫新的主題函式來產生 Flex Message
        return self.theme.create_transfer_amount_input(source_account, target_account)
    
    def _handle_amount_input(self, user_id, message, current_state):
        """處理金額輸入"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "轉帳已取消"
        
        try:
            amount = float(message.replace(',', ''))
            if amount <= 0:
                return "金額必須大於 0，請重新輸入"
            
            # 獲取完整帳戶資訊
            data = current_state['data']
            source_key = data['source_account']
            target_key = data['target_account']
            assets = self.asset_manager.get_all_assets()
            source_account = assets.get(source_key)
            target_account = assets.get(target_key)

            if not source_account or not target_account:
                self.user_state_manager.clear_user_state(user_id)
                return "發生錯誤：找不到帳戶資訊，流程已重置。"

            # 檢查餘額
            if amount > source_account['balance']:
                return f"金額超過帳戶餘額 ${source_account['balance']:,.0f}，請重新輸入"
            
            # 更新狀態
            self.user_state_manager.update_user_state(
                user_id,
                step='confirm',
                data={'amount': amount}
            )
            
            # 將完整的帳戶物件傳遞給 theme
            return self.theme.create_transfer_confirmation(source_account, target_account, amount)
            
        except ValueError:
            return "請輸入有效的數字金額"
    
    def _handle_confirmation(self, user_id, message, current_state):
        """處理確認轉帳"""
        if message == "確認轉帳":
            # 執行轉帳
            data = current_state['data']
            success, result_message = self.asset_manager.transfer(
                data['source_account'],
                data['target_account'],
                data['amount']
            )
            
            # 清除狀態
            self.user_state_manager.clear_user_state(user_id)
            
            if success:
                return self.theme.create_transfer_success(data)
            else:
                return f"轉帳失敗: {result_message}"
        
        elif message == "取消轉帳":
            self.user_state_manager.clear_user_state(user_id)
            return "轉帳已取消"
        else:
            return "請點擊「確認轉帳」或「取消轉帳」"
    
