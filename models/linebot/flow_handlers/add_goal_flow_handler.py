# models/linebot/flow_handlers/add_goal_flow_handler.py
import re
class AddGoalFlowHandler:
    """新增目標流程處理器"""
    
    def __init__(self, goal_manager, user_state_manager, operation_theme):
        self.goal_manager = goal_manager
        self.user_state_manager = user_state_manager
        self.theme = operation_theme
        
        # 目標類型選項
        self.goal_types = ["儲蓄", "投資", "債務"]
    
    def start_flow(self, user_id):
        """開始新增目標流程"""
        try:
            # 設定用戶狀態
            self.user_state_manager.set_user_state(
                user_id, 'add_goal_flow', 'input_title'
            )
            
            return self.theme.create_goal_title_input()
            
        except Exception as e:
            return f"新增目標流程啟動失敗: {str(e)}"
    
    def handle_flow_message(self, user_id, message, current_state):
        """處理新增目標流程中的訊息"""
        step = current_state['step']
        
        if step == 'input_title':
            return self._handle_title_input(user_id, message)
        elif step == 'select_type':
            return self._handle_type_selection(user_id, message, current_state)
        elif step == 'input_amount':
            return self._handle_amount_input(user_id, message, current_state)
        elif step == 'input_date':
            return self._handle_date_input(user_id, message, current_state)
        elif step == 'confirm':
            return self._handle_confirmation(user_id, message, current_state)
        else:
            self.user_state_manager.clear_user_state(user_id)
            return "新增目標流程異常，已重置。請重新開始"
    
    def _handle_title_input(self, user_id, message):
        """處理目標標題輸入"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "新增目標已取消"
        
        title = message.strip()
        if len(title) < 2:
            return self.theme.create_goal_title_input("請輸入有效的目標名稱 (至少2個字)")
        
        if len(title) > 50:
            return self.theme.create_goal_title_input("目標名稱太長，請重新輸入")
        
        # 更新狀態到下一步
        self.user_state_manager.update_user_state(
            user_id,
            step='select_type',
            data={'title': title}
        )
        
        return self.theme.create_goal_type_selection()
    
    def _handle_type_selection(self, user_id, message, current_state):
        """處理目標類型選擇"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "新增目標已取消"
        
        if not message.startswith("選擇類型:"):
            return "請點擊按鈕選擇目標類型，或輸入「取消操作」"
        
        goal_type = message.replace("選擇類型:", "")
        
        if goal_type not in self.goal_types:
            return "請選擇有效的目標類型"
        
        # 更新狀態
        self.user_state_manager.update_user_state(
            user_id,
            step='input_amount',
            data={'goal_type': goal_type}
        )
        
        return self.theme.create_goal_amount_input(goal_type)
    
    def _handle_amount_input(self, user_id, message, current_state):
        """處理目標金額輸入"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "新增目標已取消"
        
        try:
            amount = float(message.replace(',', ''))
            if amount <= 0:
                goal_type = current_state['data']['goal_type']
                return self.theme.create_goal_amount_input(goal_type, "金額必須大於0，請重新輸入")
            
            # 更新狀態
            self.user_state_manager.update_user_state(
                user_id,
                step='input_date',
                data={'target_amount': amount}
            )
            
            return self.theme.create_goal_date_input()
            
        except ValueError:
            goal_type = current_state['data']['goal_type']
            return self.theme.create_goal_amount_input(goal_type, "請輸入有效的數字金額")
    
    def _handle_date_input(self, user_id, message, current_state):
        """處理目標日期輸入"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "新增目標已取消"
        
        # 簡單的日期格式驗證
        date_pattern = r'^\d{4}-\d{2}-\d{2}'
        if not re.match(date_pattern, message):
            return self.theme.create_goal_date_input("請輸入正確的日期格式 (YYYY-MM-DD)")
        
        target_date = message
        
        # 準備確認訊息的資料
        confirmation_data = current_state['data'].copy()
        confirmation_data['target_date'] = target_date

        # 更新狀態
        self.user_state_manager.update_user_state(
            user_id,
            step='confirm',
            data={'target_date': target_date}
        )
        
        return self.theme.create_add_goal_confirmation(confirmation_data)
    
    def _handle_confirmation(self, user_id, message, current_state):
        """處理確認新增"""
        if message == "確認新增":
            # 執行新增目標
            data = current_state['data']
            success, result = self.goal_manager.add_goal(
                data['title'],
                data['goal_type'],
                data['target_amount'],
                data['target_date'],
                ""  # description 暫時為空
            )
            
            # 清除狀態
            self.user_state_manager.clear_user_state(user_id)
            
            if success:
                return self.theme.create_add_goal_success(data)
            else:
                return f"新增目標失敗: {result}"
        
        elif message == "取消新增":
            self.user_state_manager.clear_user_state(user_id)
            return "新增目標已取消"
        else:
            return "請點擊「確認新增」或「取消新增」"