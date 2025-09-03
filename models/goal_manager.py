import uuid
from datetime import datetime
from config import GOALS_FILE
from utils import load_json_file, save_json_file

class GoalManager:
    """
    管理財務目標的核心邏輯。
    負責新增、更新、刪除目標以及提供純計算功能。
    """
    def __init__(self):
        self.goal_file = GOALS_FILE
        self.goals = {}
        self.load_data()

    def load_data(self):
        """載入目標資料"""
        self.goals = load_json_file(self.goal_file, {})
        if self.goals:
            print(f"📖 載入現有目標: {len(self.goals)} 個")
        else:
            print("🆕 建立新的目標紀錄")

    def save_data(self):
        """儲存資料"""
        return save_json_file(self.goal_file, self.goals)

    def add_goal(self, title, goal_type, target_amount, target_date, description=""):
        """新增目標"""
        if target_amount <= 0:
            print("❌ 目標金額必須大於0")
            return False
    
        goal_id = str(uuid.uuid4())[:8]  # 簡化的8位ID
        self.goals[goal_id] = {
            "title": title,
            "type": goal_type,
            "target_amount": target_amount,
            "target_date": target_date,
            "current_amount": 0,
            "created_date": datetime.now().isoformat(),
            "status": "active",
            "description": description
        }
        
        if self.save_data():
            print(f"✅ 已新增目標: {title} (${target_amount:,})")
            return True
        else:
            print("❌ 新增目標失敗，無法儲存資料")
            return False
        
    def update_goal(self, goal_id, **updates):
        """
        通用更新目標方法，可同時更新多個欄位。
        傳入 goal_id 和一個包含要更新欄位的字典。
        例如: update_goal('goal123', title='新標題', target_amount=20000)
        """
        if goal_id not in self.goals:
            print("❌ 找不到此目標")
            return False

        # 檢查更新的欄位是否有效
        valid_keys = ["title", "type", "target_amount", "target_date", "current_amount", "description"]
        for key, value in updates.items():
            if key not in valid_keys:
                print(f"❌ 無效的更新欄位: {key}")
                return False

            # 特殊處理金額，確保為正數
            if key in ["target_amount", "current_amount"] and value < 0:
                print(f"❌ {key} 必須大於等於 0")
                return False

            # 更新欄位
            self.goals[goal_id][key] = value

        # 檢查是否達成目標 (如果 target_amount 或 current_amount 被更新)
        if "target_amount" in updates or "current_amount" in updates:
            target_amount = self.goals[goal_id].get("target_amount", 0)
            current_amount = self.goals[goal_id].get("current_amount", 0)
            if current_amount >= target_amount:
                self.goals[goal_id]["status"] = "completed"
            else:
                self.goals[goal_id]["status"] = "active"

        self.goals[goal_id]["last_update"] = datetime.now().isoformat()
        
        if self.save_data():
            print(f"✅ 目標「{self.goals[goal_id]['title']}」已更新")
            return True
        else:
            print("❌ 更新目標失敗，無法儲存資料")
            return False

    def update_goal_progress(self, goal_id, new_current_amount):
        """
        更新目標進度 (舊方法)
        """
        return self.update_goal(goal_id, current_amount=new_current_amount)
            
    def delete_goal(self, goal_id):
        """刪除目標"""
        if goal_id in self.goals:
            title = self.goals[goal_id]['title']
            del self.goals[goal_id]
            
            if self.save_data():
                print(f"🗑️ 已刪除目標: {title} (ID: {goal_id})")
                return True
            else:
                print("❌ 刪除目標失敗，無法儲存資料")
                return False
        else:
            print("❌ 找不到要刪除的目標")
            return False

    def get_all_goals(self):
        """回傳所有目標資料"""
        return self.goals