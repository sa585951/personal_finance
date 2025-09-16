import re

class DeleteTransactionFlowHandler:
    """刪除交易流程處理器"""
    
    def __init__(self, budget_manager, user_state_manager, operation_theme):
        self.budget_manager = budget_manager
        self.user_state_manager = user_state_manager
        self.theme = operation_theme
    
    def start_flow(self, user_id):
        """開始刪除交易流程"""
        try:
            # 獲取最近的交易記錄（限制數量避免太多）
            transactions = self.budget_manager.get_all_transactions()
            if not transactions:
                return "您還沒有任何交易記錄，無法執行刪除操作"
            
            # 只取最近20筆交易
            recent_transactions = transactions[:20]
            
            # 設定用戶狀態
            self.user_state_manager.set_user_state(
                user_id, 'delete_transaction_flow', 'select_transaction'
            )
            
            return self.theme.create_delete_transaction_selection(recent_transactions)
            
        except Exception as e:
            return f"刪除交易流程啟動失敗: {str(e)}"
    
    def handle_flow_message(self, user_id, message, current_state):
        """處理刪除交易流程中的訊息"""
        step = current_state['step']
        
        if step == 'select_transaction':
            return self._handle_transaction_selection(user_id, message)
        elif step == 'confirm':
            return self._handle_confirmation(user_id, message, current_state)
        else:
            self.user_state_manager.clear_user_state(user_id)
            return "刪除交易流程異常，已重置。請重新開始"
    
    def _handle_transaction_selection(self, user_id, message):
        """處理交易選擇"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "刪除交易已取消"
        
        # 使用正規表示式從 "選擇刪除交易: {category} ({transaction_id})" 中提取 ID
        match = re.search(r'\((\S+)\)$', message)
        if not message.startswith("選擇刪除交易:") or not match:
            return "請點擊按鈕選擇要刪除的交易，或輸入「取消操作」"
        
        transaction_id = match.group(1)
        
        # 驗證交易是否存在
        transactions = self.budget_manager.get_all_transactions()
        transactions_dict = {str(t['id']): t for t in transactions}
        selected_transaction = transactions_dict.get(transaction_id)
        
        if not selected_transaction:
            return "選擇的交易不存在，請重新選擇"
        
        # 更新狀態到確認步驟
        self.user_state_manager.update_user_state(
            user_id,
            step='confirm',
            data={'transaction_id': transaction_id, 'selected_transaction': selected_transaction}
        )
        
        return self.theme.create_delete_transaction_confirmation(selected_transaction)
    
    def _handle_confirmation(self, user_id, message, current_state):
        """處理確認刪除"""
        if message == "確認刪除":
            # 執行刪除操作
            data = current_state['data']
            success, result_message = self.budget_manager.delete_transaction(
                data['transaction_id']
            )
            
            # 清除狀態
            self.user_state_manager.clear_user_state(user_id)
            
            if success:
                return self.theme.create_delete_transaction_success(data['selected_transaction'])
            else:
                return f"刪除交易失敗: {result_message}"
        
        elif message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "刪除交易已取消"
        else:
            return "請點擊「確認刪除」或「取消刪除」"
