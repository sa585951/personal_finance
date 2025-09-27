from ...goal_manager import GoalManager

class DeleteGoalFlowHandler:
    """刪除目標流程處理器"""

    def __init__(self, user_state_manager, operation_theme):
        self.user_state_manager = user_state_manager
        self.theme = operation_theme

    def start_flow(self, user_id, db_session, goal_id=None):
        """開始刪除目標流程"""
        # goal_id is passed from message_handler when user clicks a specific goal
        if not goal_id:
            return "缺少目標 ID，無法開始刪除流程。"

        goal = GoalManager().get_goal_by_id(db_session, user_id, goal_id)
        if not goal:
            return "找不到指定的目標，請重新操作。"

        self.user_state_manager.set_user_state(
            user_id,
            'delete_goal_flow',
            'confirm',
            data={'goal': goal}
        )
        return self.theme.create_delete_goal_confirmation(goal)

    def handle_flow_message(self, user_id, message, current_state, db_session):
        """處理刪除目標流程中的訊息"""
        step = current_state.get('step')

        if step == 'confirm':
            return self._handle_confirmation(user_id, message, current_state, db_session)
        else:
            self.user_state_manager.clear_user_state(user_id)
            return "刪除目標流程異常，已重置。"

    def _handle_confirmation(self, user_id, message, current_state, db_session):
        """處理確認刪除"""
        if message == "確認刪除":
            goal = current_state['data']['goal']
            goal_id = goal['id']
            
            GoalManager().delete_goal(db_session, user_id, goal_id)
            
            self.user_state_manager.clear_user_state(user_id)
            return self.theme.create_delete_goal_success(goal)
        
        elif message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "刪除操作已取消"
        else:
            goal = current_state['data']['goal']
            return self.theme.create_delete_goal_confirmation(goal, "請點擊「確認刪除」或「取消操作」")