import re
from ...budget_manager import BudgetManager

class DeleteTransactionFlowHandler:
    """刪除交易流程處理器"""
    
    def __init__(self, user_state_manager, operation_theme):
        self.user_state_manager = user_state_manager
        self.theme = operation_theme
    
    def start_flow(self, user_id, db_session):
        """開始刪除交易流程"""
        transactions = BudgetManager().get_all_transactions(db_session, user_id)
        if not transactions:
            return "您還沒有任何交易記錄，無法執行刪除操作"
        
        recent_transactions = transactions[:20]
        
        self.user_state_manager.set_user_state(
            user_id, 'delete_transaction_flow', 'select_transaction'
        )
        
        return self.theme.create_delete_transaction_selection(recent_transactions)
            
    def handle_flow_message(self, user_id, message, current_state, db_session):
        """處理刪除交易流程中的訊息"""
        step = current_state['step']
        
        if step == 'select_transaction':
            return self._handle_transaction_selection(user_id, message, db_session)
        elif step == 'confirm':
            return self._handle_confirmation(user_id, message, current_state, db_session)
        else:
            self.user_state_manager.clear_user_state(user_id)
            return "刪除交易流程異常，已重置。"
    
    def _handle_transaction_selection(self, user_id, message, db_session):
        """處理交易選擇"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "刪除交易已取消"
        
        match = re.search(r'\((\S+)\)$', message)
        if not message.startswith("選擇刪除交易:") or not match:
            return "請點擊按鈕選擇要刪除的交易，或輸入「取消操作」"
        
        transaction_id = match.group(1)
        
        transactions = BudgetManager().get_all_transactions(db_session, user_id)
        transactions_dict = {str(t['id']): t for t in transactions}
        selected_transaction = transactions_dict.get(transaction_id)
        
        if not selected_transaction:
            return "選擇的交易不存在，請重新選擇"
        
        self.user_state_manager.update_user_state(
            user_id,
            step='confirm',
            data={'transaction_id': transaction_id, 'selected_transaction': selected_transaction}
        )
        return self.theme.create_delete_transaction_confirmation(selected_transaction)
    
    def _handle_confirmation(self, user_id, message, current_state, db_session):
        """處理確認刪除"""
        if message == "確認刪除":
            data = current_state['data']
            transaction_id = data['transaction_id']
            
            BudgetManager().delete_transaction(db_session, user_id, transaction_id)
            
            self.user_state_manager.clear_user_state(user_id)
            return self.theme.create_delete_transaction_success(data['selected_transaction'])
        
        elif message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "刪除交易已取消"
        else:
            return "請點擊「確認刪除」或「取消刪除」"