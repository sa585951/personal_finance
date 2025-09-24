from datetime import datetime
from sqlalchemy import select, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .database import engine as global_engine
from .schema import users_table

class UserManager:
    """管理使用者資料，包含新增和查詢使用者。"""

    def __init__(self, engine=None):
        self.engine = engine or global_engine

    def get_or_create_user(self, user_id, display_name=None):
        """根據 user_id 獲取使用者，如果不存在則創建新使用者。"""
        with self.engine.connect() as conn:
            # 嘗試獲取使用者
            stmt = select(users_table).where(users_table.c.user_id == user_id)
            existing_user = conn.execute(stmt).first()

            if existing_user:
                # 如果使用者存在，檢查 display_name 是否需要更新
                if display_name and existing_user.display_name != display_name:
                    update_stmt = users_table.update().where(users_table.c.user_id == user_id).values(display_name=display_name)
                    conn.execute(update_stmt)
                    conn.commit()
                    return {**dict(existing_user._mapping), "display_name": display_name}
                return dict(existing_user._mapping)
            else:
                # 如果使用者不存在，則創建新使用者
                insert_stmt = insert(users_table).values(
                    user_id=user_id,
                    display_name=display_name,
                    created_at=datetime.now()
                )
                conn.execute(insert_stmt)
                conn.commit()
                return {
                    "user_id": user_id,
                    "display_name": display_name,
                    "created_at": datetime.now()
                }
