from datetime import datetime
from sqlalchemy import select, insert, update, delete

from .database import engine
from .schema import goals_table

class GoalManager:
    """管理財務目標，所有操作直接對資料庫進行。"""

    def get_all_goals(self):
        """從資料庫獲取所有目標"""
        stmt = select(goals_table)
        with engine.connect() as conn:
            result = conn.execute(stmt)
            goals = [dict(row._mapping) for row in result]
            return goals

    def add_goal(self, title, goal_type, target_amount, target_date, description=""):
        """新增一個目標到資料庫"""
        if target_amount <= 0:
            return False, "目標金額必須大於0"

        stmt = insert(goals_table).values(
            title=title,
            type=goal_type,
            target_amount=target_amount,
            target_date=target_date,
            current_amount=0,
            created_date=datetime.now(),
            last_update=datetime.now(),
            status="active",
            description=description
        )
        
        with engine.connect() as conn:
            try:
                result = conn.execute(stmt)
                conn.commit()
                # 返回帶有新 ID 的成功訊息
                new_id = result.inserted_primary_key[0]
                print(f"✅ 已新增目標 '{title}' 到資料庫，ID: {new_id}")
                return True, {"id": new_id}
            except Exception as e:
                print(f"❌ 新增目標失敗: {e}")
                return False, f"新增目標失敗: {e}"

    def update_goal(self, goal_id, **updates):
        """通用更新目標方法，可同時更新多個欄位"""
        with engine.connect() as conn:
            # 1. 先獲取目標的當前狀態
            goal_stmt = select(goals_table).where(goals_table.c.id == goal_id)
            current_goal = conn.execute(goal_stmt).first()
            if not current_goal:
                return False, "找不到此目標"

            # 2. 準備要更新的資料
            update_values = updates.copy()
            update_values['last_update'] = datetime.now()

            # 3. 檢查並更新目標狀態
            current_amount = update_values.get("current_amount", current_goal.current_amount)
            target_amount = update_values.get("target_amount", current_goal.target_amount)
            
            if current_amount >= target_amount:
                update_values['status'] = "completed"
            else:
                update_values['status'] = "active"

            # 4. 執行更新
            stmt = update(goals_table).where(goals_table.c.id == goal_id).values(**update_values)
            conn.execute(stmt)
            conn.commit()
            print(f"✅ 已更新目標 ID: {goal_id}")
            return True, "目標更新成功"

    def delete_goal(self, goal_id):
        """從資料庫刪除目標"""
        stmt = delete(goals_table).where(goals_table.c.id == goal_id)
        with engine.connect() as conn:
            result = conn.execute(stmt)
            conn.commit()
            if result.rowcount == 0:
                print(f"❌ 刪除失敗: 找不到目標 ID: {goal_id}")
                return False, "找不到要刪除的目標"
            print(f"🗑️ 已從資料庫刪除目標 ID: {goal_id}")
            return True, "成功刪除目標"

    def calculate_goal_summary(self):
        """計算所有目標的總覽"""
        all_goals = self.get_all_goals()
        summary = {
            "total_goals": len(all_goals),
            "active_goals": 0,
            "completed_goals": 0,
            "total_needed": 0,
            "total_saved": 0,
        }
        for goal in all_goals.values():
            if goal["status"] == "active":
                summary["active_goals"] += 1
            else:
                summary["completed_goals"] += 1
            
            summary["total_needed"] += goal["target_amount"]
            summary["total_saved"] += goal["current_amount"]
        
        return summary
