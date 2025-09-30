import re
from ...goal_manager import GoalManager

class EditGoalFlowHandler:
    """為目標增加進度流程處理器"""

    def __init__(self, user_state_manager, operation_theme, goal_manager):
        self.user_state_manager = user_state_manager
        self.theme = operation_theme
        self.goal_manager = goal_manager

    def start_flow(self, user_id, goal_id=None):
        """開始為目標增加進度流程"""
        if not goal_id:
            return "缺少目標 ID，無法開始編輯流程。"
            
        goal = self.goal_manager.get_goal_by_id(user_id, goal_id)
        if not goal:
            return "找不到指定的目標，請重新操作。"

        self.user_state_manager.set_user_state(
            user_id, 
            'edit_goal_flow', 
            'input_amount_to_add',
            data={'goal': goal}
        )
        return self.theme.create_add_goal_progress_input(goal)
            
    def handle_flow_message(self, user_id, message, current_state):
        """處理增加進度流程中的訊息"""
        step = current_state.get('step')
        
        if step == 'input_amount_to_add':
            return self._handle_amount_input(user_id, message, current_state)
        else:
            self.user_state_manager.clear_user_state(user_id)
            return "編輯目標流程異常，已重置。"

    def _handle_amount_input(self, user_id, message, current_state):
        """處理金額輸入"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "操作已取消"

        goal = current_state['data']['goal']
        
        try:
            amount_to_add = float(message.replace(',', ''))
            if amount_to_add <= 0:
                return self.theme.create_add_goal_progress_input(goal, "增加的金額必須大於 0，請重新輸入。")
        except ValueError:
            return self.theme.create_add_goal_progress_input(goal, "請輸入有效的數字金額。")

        self.goal_manager.add_goal_progress(user_id, goal['id'], amount_to_add)
        
        self.user_state_manager.clear_user_state(user_id)
        
        # 獲取更新後的目標狀態並回傳
        updated_goal = self.goal_manager.get_goal_by_id(user_id, goal['id'])
        return self.theme.create_add_goal_progress_success(updated_goal, amount_to_add)