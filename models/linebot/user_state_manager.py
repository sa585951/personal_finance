from datetime import datetime, timedelta

class UserStateManager:
    """用戶狀態管理器 - 處理多步驟流程的狀態"""
    
    def __init__(self, state_timeout_minutes=10):
        """
        初始化狀態管理器
        
        Args:
            state_timeout_minutes (int): 狀態過期時間（分鐘）
        """
        self.user_states = {}  # 儲存每個用戶的操作狀態
        self.state_timeout = timedelta(minutes=state_timeout_minutes)
    
    def set_user_state(self, user_id, state_type, step, data=None):
        """
        設定用戶狀態
        
        Args:
            user_id (str): 用戶 ID
            state_type (str): 狀態類型 ('transfer_flow', 'add_account_flow')
            step (str): 當前步驟
            data (dict): 狀態資料
        """
        self.user_states[user_id] = {
            'type': state_type,
            'step': step,
            'data': data or {},
            'timestamp': datetime.now()
        }
    
    def get_user_state(self, user_id):
        """
        獲取用戶狀態
        
        Args:
            user_id (str): 用戶 ID
            
        Returns:
            dict or None: 用戶狀態，如果過期或不存在則返回 None
        """
        if user_id not in self.user_states:
            return None
        
        state = self.user_states[user_id]
        
        # 檢查狀態是否過期
        if datetime.now() - state['timestamp'] > self.state_timeout:
            del self.user_states[user_id]
            return None
        
        return state
    
    def update_user_state(self, user_id, step=None, data=None):
        """
        更新用戶狀態
        
        Args:
            user_id (str): 用戶 ID
            step (str, optional): 新的步驟
            data (dict, optional): 要更新或新增的資料
        """
        if user_id not in self.user_states:
            return False
        
        if step:
            self.user_states[user_id]['step'] = step
        
        if data:
            self.user_states[user_id]['data'].update(data)
        
        self.user_states[user_id]['timestamp'] = datetime.now()
        return True
    
    def clear_user_state(self, user_id):
        """
        清除用戶狀態
        
        Args:
            user_id (str): 用戶 ID
        """
        if user_id in self.user_states:
            del self.user_states[user_id]
    
    def cleanup_expired_states(self):
        """清理過期的狀態"""
        current_time = datetime.now()
        expired_users = [
            user_id for user_id, state in self.user_states.items()
            if current_time - state['timestamp'] > self.state_timeout
        ]
        
        for user_id in expired_users:
            del self.user_states[user_id]
        
        return len(expired_users)