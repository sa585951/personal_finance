# models/goal_manager.py

from datetime import datetime
from sqlalchemy import select, insert, update, delete

from .schema import goals_table

class GoalManager:
    """管理財務目標，所有操作都透過傳入的 db_session 進行。"""

    def get_all_goals(self, db_session, user_id):
        """從資料庫獲取指定使用者的所有目標"""
        stmt = select(goals_table).where(goals_table.c.user_id == user_id)
        result = db_session.execute(stmt)
        return [dict(row._mapping) for row in result]

    def get_goal_by_id(self, db_session, user_id, goal_id):
        """根據 ID 從資料庫獲取指定使用者的單個目標"""
        stmt = select(goals_table).where(goals_table.c.user_id == user_id, goals_table.c.id == goal_id)
        result = db_session.execute(stmt).first()
        if result:
            return dict(result._mapping)
        return None

    def add_goal(self, db_session, user_id, title, type, target_amount, target_date, description=""):
        """新增一個目標到資料庫，並與使用者綁定"""
        if target_amount <= 0:
            raise ValueError("目標金額必須大於0")

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
        ).returning(goals_table.c.id)
        
        result = db_session.execute(stmt)
        new_id = result.scalar_one()
        print(f"✅ 已新增目標 '{title}' 到資料庫，ID: {new_id}")
        return True, {"id": new_id}

    def add_goal_progress(self, db_session, user_id, goal_id, amount_to_add):
        """為指定使用者的目標增加已存金額（進度）"""
        if amount_to_add <= 0:
            raise ValueError("增加的金額必須大於0")

        goal_stmt = select(goals_table).where(
            goals_table.c.user_id == user_id, 
            goals_table.c.id == goal_id
        ).with_for_update()
        current_goal = db_session.execute(goal_stmt).first()

        if not current_goal:
            raise ValueError("找不到此目標或權限不足")

        new_current_amount = current_goal.current_amount + amount_to_add
        new_status = "completed" if new_current_amount >= current_goal.target_amount else current_goal.status
        
        update_stmt = (
            update(goals_table)
            .where(goals_table.c.id == goal_id)
            .values(current_amount=new_current_amount, status=new_status, last_update=datetime.now())
        )
        db_session.execute(update_stmt)
        
        print(f"✅ 已為目標 ID: {goal_id} 增加進度 {amount_to_add}")
        return True, "目標進度更新成功"

    def update_goal(self, db_session, user_id, goal_id, **updates):
        """通用更新目標方法，可同時更新多個欄位，並驗證使用者"""
        goal_stmt = select(goals_table).where(goals_table.c.user_id == user_id, goals_table.c.id == goal_id)
        current_goal = db_session.execute(goal_stmt).first()
        if not current_goal:
            raise ValueError("找不到此目標或權限不足")

        update_values = updates.copy()
        update_values['last_update'] = datetime.now()

        current_amount = update_values.get("current_amount", current_goal.current_amount)
        target_amount = update_values.get("target_amount", current_goal.target_amount)
        
        update_values['status'] = "completed" if current_amount >= target_amount else "active"

        stmt = update(goals_table).where(goals_table.c.id == goal_id).values(**update_values)
        db_session.execute(stmt)
        print(f"✅ 已更新目標 ID: {goal_id}")
        return True, "目標更新成功"

    def delete_goal(self, db_session, user_id, goal_id):
        """從資料庫刪除目標，並驗證使用者"""
        stmt = delete(goals_table).where(goals_table.c.user_id == user_id, goals_table.c.id == goal_id)
        result = db_session.execute(stmt)
        if result.rowcount == 0:
            raise ValueError("找不到要刪除的目標或權限不足")
        print(f"🗑️ 已從資料庫刪除目標 ID: {goal_id}")
        return True, "成功刪除目標"

    def calculate_goal_summary(self, db_session, user_id):
        """計算指定使用者的所有目標的總覽"""
        summary = {
            "total_goals": 0, "active_goals": 0, "completed_goals": 0,
            "total_target_amount": 0, "total_current_amount": 0,
            "overall_progress_percentage": 0
        }
        all_goals = self.get_all_goals(db_session, user_id)
        
        summary["total_goals"] = len(all_goals)
        if not all_goals:
            return summary

        for goal in all_goals:
            if goal["status"] == "active":
                summary["active_goals"] += 1
            else:
                summary["completed_goals"] += 1
            summary["total_target_amount"] += goal["target_amount"]
            summary["total_current_amount"] += goal["current_amount"]
        
        summary["total_target_amount"] = float(summary["total_target_amount"])
        summary["total_current_amount"] = float(summary["total_current_amount"])

        if summary["total_target_amount"] > 0:
            summary["overall_progress_percentage"] = (summary["total_current_amount"] / summary["total_target_amount"]) * 100
        
        return summary