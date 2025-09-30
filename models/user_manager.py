# models/user_manager.py

from datetime import datetime
from sqlalchemy import select, update, insert

from .schema import users_table

class UserManager:
    """管理使用者資料，包含新增和查詢使用者。"""
    def __init__(self, db_session):
        self.db_session = db_session

    def get_or_create_user(self, user_id, display_name=None):
        """根據 user_id 獲取使用者，如果不存在則創建新使用者。
        
        Args:
            user_id (str): 使用者的 Line User ID。
            display_name (str, optional): 使用者的 Line 顯示名稱。

        Returns:
            dict: 使用者資料。
        """
        # 嘗試獲取使用者
        stmt = select(users_table).where(users_table.c.user_id == user_id)
        existing_user = self.db_session.execute(stmt).first()

        if existing_user:
            # 如果使用者存在，且 display_name 有變化，則更新
            if display_name and existing_user.display_name != display_name:
                update_stmt = (
                    update(users_table)
                    .where(users_table.c.user_id == user_id)
                    .values(display_name=display_name)
                )
                self.db_session.execute(update_stmt)
                # 返回更新後的資料
                return {**dict(existing_user._mapping), "display_name": display_name}
            return dict(existing_user._mapping)
        else:
            # 如果使用者不存在，則創建新使用者
            insert_stmt = insert(users_table).values(
                user_id=user_id,
                display_name=display_name,
                created_at=datetime.now()
            )
            self.db_session.execute(insert_stmt)
            # 獲取剛剛插入的資料並返回
            new_user = self.db_session.execute(stmt).first()
            return dict(new_user._mapping)