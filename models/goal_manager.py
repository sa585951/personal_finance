from datetime import datetime
from sqlalchemy import select, insert, update, delete

from .database import engine as global_engine # Rename to avoid conflict
from .schema import goals_table

class GoalManager:
    """管理財務目標，所有操作直接對資料庫進行。"""

    def __init__(self, engine=None):
        self.engine = engine or global_engine

    def get_all_goals(self, user_id):
        """從資料庫獲取指定使用者的所有目標"""
        stmt = select(goals_table).where(goals_table.c.user_id == user_id)
        with self.engine.connect() as conn:
            result = conn.execute(stmt)
            goals = [dict(row._mapping) for row in result]
            return goals

    def get_goal_by_id(self, user_id, goal_id):
        """根據 ID 從資料庫獲取指定使用者的單個目標"""
        stmt = select(goals_table).where(goals_table.c.user_id == user_id, goals_table.c.id == goal_id)
        with self.engine.connect() as conn:
            result = conn.execute(stmt).first()
            if result:
                return dict(result._mapping)
            return None

    def add_goal(self, user_id, title, type, target_amount, target_date, description=""):
        """新增一個目標到資料庫，並與使用者綁定"""
        if target_amount <= 0:
            return False, "目標金額必須大於0"

        stmt = insert(goals_table).values(
            user_id=user_id,
            title=title,
            type=type,
            target_amount=target_amount,
            target_date=target_date,
            current_amount=0,
            created_date=datetime.now(),
            last_update=datetime.now(),
            status="active",
            description=description
        )
        
        with self.engine.connect() as conn:
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

    def add_goal_progress(self, user_id, goal_id, amount_to_add):
        """為指定使用者的目標增加已存金額（進度）"""
        if amount_to_add <= 0:
            return False, "增加的金額必須大於0"

        with self.engine.connect() as conn:
            with conn.begin() as transaction:
                try:
                    # 1. 鎖定並獲取當前目標，同時驗證使用者
                    goal_stmt = select(goals_table).where(
                        goals_table.c.user_id == user_id, 
                        goals_table.c.id == goal_id
                    ).with_for_update()
                    current_goal = conn.execute(goal_stmt).first()

                    if not current_goal:
                        return False, "找不到此目標或權限不足"

                    # 2. 計算新金額和狀態
                    new_current_amount = current_goal.current_amount + amount_to_add
                    new_status = current_goal.status
                    if new_current_amount >= current_goal.target_amount:
                        new_status = "completed"
                    
                    # 3. 執行更新
                    update_stmt = (
                        update(goals_table)
                        .where(goals_table.c.user_id == user_id, goals_table.c.id == goal_id)
                        .values(
                            current_amount=new_current_amount,
                            status=new_status,
                            last_update=datetime.now()
                        )
                    )
                    conn.execute(update_stmt)
                    
                    print(f"✅ 已為目標 ID: {goal_id} 增加進度 {amount_to_add}")
                    return True, "目標進度更新成功"
                except Exception as e:
                    print(f"❌ 更新目標進度失敗: {e}")
                    transaction.rollback()
                    return False, "更新目標進度時發生錯誤"

    def update_goal(self, user_id, goal_id, **updates):
        """通用更新目標方法，可同時更新多個欄位，並驗證使用者"""
        with self.engine.connect() as conn:
            # 1. 先獲取目標的當前狀態，並驗證使用者
            goal_stmt = select(goals_table).where(goals_table.c.user_id == user_id, goals_table.c.id == goal_id)
            current_goal = conn.execute(goal_stmt).first()
            if not current_goal:
                return False, "找不到此目標或權限不足"

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
            stmt = update(goals_table).where(goals_table.c.user_id == user_id, goals_table.c.id == goal_id).values(**update_values)
            conn.execute(stmt)
            conn.commit()
            print(f"✅ 已更新目標 ID: {goal_id}")
            return True, "目標更新成功"

    def delete_goal(self, user_id, goal_id):
        """從資料庫刪除目標，並驗證使用者"""
        stmt = delete(goals_table).where(goals_table.c.user_id == user_id, goals_table.c.id == goal_id)
        with self.engine.connect() as conn:
            result = conn.execute(stmt)
            conn.commit()
            if result.rowcount == 0:
                print(f"❌ 刪除失敗: 找不到目標 ID: {goal_id} 或權限不足")
                return False, "找不到要刪除的目標"
            print(f"🗑️ 已從資料庫刪除目標 ID: {goal_id}")
            return True, "成功刪除目標"

    def calculate_goal_summary(self, user_id):
        """計算指定使用者的所有目標的總覽"""
        all_goals = self.get_all_goals(user_id)
        summary = {
            "total_goals": len(all_goals),
            "active_goals": 0,
            "completed_goals": 0,
            "total_target_amount": 0,
            "total_current_amount": 0,
            "overall_progress_percentage": 0
        }
        for goal in all_goals:
            if goal["status"] == "active":
                summary["active_goals"] += 1
            else:
                summary["completed_goals"] += 1
            
            summary["total_target_amount"] += goal["target_amount"]
            summary["total_current_amount"] += goal["current_amount"]
        
        # 將 Decimal 轉換為 float 以便進行 JSON 序列化
        summary["total_target_amount"] = float(summary["total_target_amount"])
        summary["total_current_amount"] = float(summary["total_current_amount"])

        if summary["total_target_amount"] > 0:
            summary["overall_progress_percentage"] = (summary["total_current_amount"] / summary["total_target_amount"]) * 100
        else:
            summary["overall_progress_percentage"] = 0

        return summary
