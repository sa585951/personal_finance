import re
from datetime import datetime

class EditGoalFlowHandler:
    """編輯目標流程處理器"""

    def __init__(self, goal_manager, user_state_manager, operation_theme):
        self.goal_manager = goal_manager
        self.user_state_manager = user_state_manager
        self.theme = operation_theme
        self.editable_fields = {
            "名稱": "title",
            "金額": "target_amount",
            "日期": "target_date"
        }

    def start_flow(self, user_id, goal_id):
        """開始編輯目標流程"""
        try:
            goal = self.goal_manager.get_goal_by_id(goal_id)
            if not goal:
                return "找不到指定的目標，請重新操作。"

            # Set user state
            self.user_state_manager.set_user_state(
                user_id, 
                'edit_goal_flow', 
                'select_field',
                data={'goal': goal}
            )
            
            return self.theme.create_edit_goal_selection(goal, list(self.editable_fields.keys()))
            
        except Exception as e:
            return f"編輯目標流程啟動失敗: {str(e)}"

    def handle_flow_message(self, user_id, message, current_state):
        """處理編輯目標流程中的訊息"""
        step = current_state.get('step')
        
        if step == 'select_field':
            return self._handle_field_selection(user_id, message, current_state)
        elif step == 'input_new_value':
            return self._handle_new_value_input(user_id, message, current_state)
        elif step == 'confirm_edit':
            return self._handle_confirmation(user_id, message, current_state)
        else:
            self.user_state_manager.clear_user_state(user_id)
            return "編輯目標流程異常，已重置。"

    def _handle_field_selection(self, user_id, message, current_state):
        """處理欄位選擇"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "編輯操作已取消"

        # 檢查使用者是否點擊了舊的按鈕，導致流程問題
        if "start_edit_goal" in message or "start_delete_goal" in message:
            goal = current_state['data']['goal']
            return self.theme.create_edit_goal_selection(goal, list(self.editable_fields.keys()), "您已在編輯流程中，請點擊下方按鈕選擇要編輯的欄位，或輸入「取消操作」。")

        field_to_edit = message.replace("選擇編輯:", "").strip()
        if field_to_edit not in self.editable_fields:
            goal = current_state['data']['goal']
            return self.theme.create_edit_goal_selection(goal, list(self.editable_fields.keys()), "請點擊下方按鈕選擇有效的欄位")

        self.user_state_manager.update_user_state(
            user_id,
            step='input_new_value',
            data={'field_to_edit': field_to_edit}
        )
        
        goal = current_state['data']['goal']
        return self.theme.create_edit_goal_field_input(field_to_edit, goal)

    def _handle_new_value_input(self, user_id, message, current_state):
        """處理新值輸入"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "編輯操作已取消"

        field = current_state['data']['field_to_edit']
        new_value = message.strip()
        goal = current_state['data']['goal']

        # 驗證新值
        validation_error = None
        if field == "金額":
            try:
                new_value = float(new_value.replace(',', ''))
                if new_value <= 0:
                    validation_error = "金額必須大於0，請重新輸入"
            except ValueError:
                validation_error = "請輸入有效的數字金額"
        elif field == "日期":
            date_pattern = r'^\d{4}-\d{2}-\d{2}'

            if not re.match(date_pattern, new_value):
                validation_error = "請輸入正確的日期格式 (YYYY-MM-DD)"
            else:
                try:
                    datetime.strptime(new_value, "%Y-%m-%d")
                except ValueError:
                    validation_error = "日期無效，請重新輸入 (YYYY-MM-DD)"
        
        if validation_error:
            return self.theme.create_edit_goal_field_input(field, goal, validation_error)

        # 更新狀態
        self.user_state_manager.update_user_state(
            user_id,
            step='confirm_edit',
            data={'new_value': new_value}
        )
        
        goal_data = current_state['data']
        return self.theme.create_edit_goal_confirmation(
            goal=goal_data['goal'],
            field=goal_data['field_to_edit'],
            new_value=new_value
        )

    def _handle_confirmation(self, user_id, message, current_state):
        """處理最終確認"""
        if message == "確認修改":
            data = current_state['data']
            goal = data['goal']
            field = data['field_to_edit']
            new_value = data['new_value']
            
            # 將欄位名稱映射到資料庫欄位名
            db_field = self.editable_fields[field]
            
            # 轉換值為正確的類型
            if field == "金額":
                new_value = float(new_value) # 已經在_handle_new_value_input中驗證並轉換
            elif field == "日期":
                new_value = datetime.strptime(new_value, "%Y-%m-%d").date() # 儲存為日期對象

            success, msg = self.goal_manager.update_goal(goal['id'], **{db_field: new_value})
            
            self.user_state_manager.clear_user_state(user_id)
            
            if success:
                return self.theme.create_edit_goal_success(goal, field, new_value)
            else:
                return f"更新目標失敗: {msg}"
        
        elif message == "取消修改":
            self.user_state_manager.clear_user_state(user_id)
            return "修改操作已取消"
        else:
            return "請點擊「確認修改」或「取消修改」"
