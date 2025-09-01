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

    def update_goal_progress(self, goal_id, new_current_amount):
        """更新目標進度"""
        if goal_id not in self.goals:
            print("❌ 找不到此目標")
            return False
        
        if new_current_amount < 0:
            print("❌ 金額不能為負數")
            return False
        
        old_amount = self.goals[goal_id]["current_amount"]
        target_amount = self.goals[goal_id]["target_amount"]

        # 更新進度
        self.goals[goal_id]["current_amount"] = new_current_amount
        self.goals[goal_id]["last_update"] = datetime.now().isoformat()

        # 檢查是否達成目標
        if new_current_amount >= target_amount:
            self.goals[goal_id]["status"] = "completed"
            
        if self.save_data():
            # 顯示進度變化
            progress = (new_current_amount / target_amount * 100) if target_amount > 0 else 0
            change = new_current_amount - old_amount
            print(f"📈 進度更新: ${old_amount:,} → ${new_current_amount:,} ({change:+,})")
            print(f"📊 目標達成率: {progress:.1f}%")
            if new_current_amount >= target_amount:
                print(f"🎉 恭喜！目標「{self.goals[goal_id]['title']}」已達成！")
            return True
        else:
            print("❌ 更新目標失敗，無法儲存資料")
            return False
            
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