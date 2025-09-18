class DeleteGoalFlowHandler:
    """刪除目標流程處理器"""

    def __init__(self, goal_manager, user_state_manager, operation_theme):
        self.goal_manager = goal_manager
        self.user_state_manager = user_state_manager
        self.theme = operation_theme

    def start_flow(self, user_id, goal_id):
        """開始刪除目標流程"""
        try:
            goal = self.goal_manager.get_goal_by_id(goal_id)
            if not goal:
                return "找不到指定的目標，請重新操作。"

            # 設定用戶狀態，直接進入確認步驟
            self.user_state_manager.set_user_state(
                user_id,
                'delete_goal_flow',
                'confirm',
                data={'goal': goal}
            )
            
            return self.theme.create_delete_goal_confirmation(goal)

        except Exception as e:
            return f"刪除目標流程啟動失敗: {str(e)}"

    def handle_flow_message(self, user_id, message, current_state):
        """處理刪除目標流程中的訊息"""
        step = current_state.get('step')

        if step == 'confirm':
            return self._handle_confirmation(user_id, message, current_state)
        else:
            self.user_state_manager.clear_user_state(user_id)
            return "刪除目標流程異常，已重置。"

    def _handle_confirmation(self, user_id, message, current_state):
        """處理確認刪除"""
        if message == "確認刪除":
            goal = current_state['data']['goal']
            goal_id = goal['id']
            
            success, msg = self.goal_manager.delete_goal(goal_id)
            
            self.user_state_manager.clear_user_state(user_id)
            
            if success:
                return self.theme.create_delete_goal_success(goal)
            else:
                return f"刪除目標失敗: {msg}"
        
        elif message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "刪除操作已取消"
        else:
            goal = current_state['data']['goal']
            return self.theme.create_delete_goal_confirmation(goal, "請點擊「確認刪除」或「取消操作」")
