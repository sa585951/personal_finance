import re
from ...goal_manager import GoalManager

class AddGoalFlowHandler:
    """新增目標流程處理器"""
    
    def __init__(self, user_state_manager, operation_theme):
        self.user_state_manager = user_state_manager
        self.theme = operation_theme
        self.goal_types = ["儲蓄", "投資", "債務"]
    
    def start_flow(self, user_id, db_session=None):
        """開始新增目標流程"""
        self.user_state_manager.set_user_state(
            user_id, 'add_goal_flow', 'input_title'
        )
        return self.theme.create_goal_title_input()
    
    def handle_flow_message(self, user_id, message, current_state, db_session):
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
            return self._handle_confirmation(user_id, message, current_state, db_session)
        else:
            self.user_state_manager.clear_user_state(user_id)
            return "新增目標流程異常，已重置。"
    
    def _handle_title_input(self, user_id, message):
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "新增目標已取消"
        
        title = message.strip()
        if len(title) < 2:
            return self.theme.create_goal_title_input("請輸入有效的目標名稱 (至少2個字)")
        
        if len(title) > 50:
            return self.theme.create_goal_title_input("目標名稱太長，請重新輸入")
        
        self.user_state_manager.update_user_state(
            user_id,
            step='select_type',
            data={'title': title}
        )
        return self.theme.create_goal_type_selection()
    
    def _handle_type_selection(self, user_id, message, current_state):
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "新增目標已取消"
        
        if not message.startswith("選擇類型:"):
            return "請點擊按鈕選擇目標類型，或輸入「取消操作」"
        
        selected_type = message.replace("選擇類型:", "")
        
        if selected_type not in self.goal_types:
            return "請選擇有效的目標類型"
        
        self.user_state_manager.update_user_state(
            user_id,
            step='input_amount',
            data={'type': selected_type}
        )
        return self.theme.create_goal_amount_input(selected_type)
    
    def _handle_amount_input(self, user_id, message, current_state):
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "新增目標已取消"
        
        try:
            amount = float(message.replace(',', ''))
            if amount <= 0:
                selected_type = current_state['data']['type']
                return self.theme.create_goal_amount_input(selected_type, "金額必須大於0，請重新輸入")
            
            self.user_state_manager.update_user_state(
                user_id,
                step='input_date',
                data={'target_amount': amount}
            )
            return self.theme.create_goal_date_input()
        except ValueError:
            selected_type = current_state['data']['type']
            return self.theme.create_goal_amount_input(selected_type, "請輸入有效的數字金額")
    
    def _handle_date_input(self, user_id, message, current_state):
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "新增目標已取消"
        
        date_pattern = r'^\d{4}-\d{2}-\d{2}'
        if not re.match(date_pattern, message):
            return self.theme.create_goal_date_input("請輸入正確的日期格式 (YYYY-MM-DD)")
        
        target_date = message
        
        confirmation_data = current_state['data'].copy()
        confirmation_data['target_date'] = target_date

        self.user_state_manager.update_user_state(
            user_id,
            step='confirm',
            data={'target_date': target_date}
        )
        return self.theme.create_add_goal_confirmation(confirmation_data)
    
    def _handle_confirmation(self, user_id, message, current_state, db_session):
        """處理確認新增"""
        if message == "確認新增":
            data = current_state['data']
            
            GoalManager().add_goal(
                db_session,
                user_id,
                data["title"],
                data["type"],
                data["target_amount"],
                data["target_date"],
                description=""
            )

            self.user_state_manager.clear_user_state(user_id)
            return self.theme.create_add_goal_success(data)

        elif message == "取消新增":
            self.user_state_manager.clear_user_state(user_id)
            return "新增目標已取消"
        else:
            return "請點擊「確認新增」或「取消新增」"