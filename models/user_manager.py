from sqlalchemy import insert, select, update

from .schema import user_identities_table, users_table

class UserManager:
    """管理使用者與第三方登入身份。"""

    def __init__(self, db_session):
        self.db_session = db_session

    def get_user_by_identity(self, provider, provider_user_id):
        """透過第三方 provider 身份查詢內部使用者。"""
        stmt = (
            select(users_table)
            .join(user_identities_table, users_table.c.id == user_identities_table.c.user_id)
            .where(
                user_identities_table.c.provider == provider,
                user_identities_table.c.provider_user_id == provider_user_id,
                users_table.c.deleted_at.is_(None),
            )
        )
        row = self.db_session.execute(stmt).first()
        return dict(row._mapping) if row else None

    def get_or_create_user_for_identity(
        self,
        provider,
        provider_user_id,
        display_name=None,
        provider_email=None,
        avatar_url=None,
        base_currency="TWD",
        locale="zh-TW",
        timezone="Asia/Taipei",
    ):
        """根據第三方登入身份取得或建立內部使用者。

        內部使用者一律使用 users.id UUID；LINE / Google / Apple 等外部 ID
        存在 user_identities，避免未來新增登入方式時重工。
        """
        existing_user = self.get_user_by_identity(provider, provider_user_id)
        if existing_user:
            update_values = {}
            if display_name and existing_user.get("display_name") != display_name:
                update_values["display_name"] = display_name
            if provider_email and existing_user.get("email") != provider_email:
                update_values["email"] = provider_email
            if avatar_url and existing_user.get("avatar_url") != avatar_url:
                update_values["avatar_url"] = avatar_url

            if update_values:
                self.db_session.execute(
                    update(users_table)
                    .where(users_table.c.id == existing_user["id"])
                    .values(**update_values)
                )
                existing_user.update(update_values)

            identity_update_values = {}
            if provider_email:
                identity_update_values["provider_email"] = provider_email
            if display_name:
                identity_update_values["provider_display_name"] = display_name

            if identity_update_values:
                self.db_session.execute(
                    update(user_identities_table)
                    .where(
                        user_identities_table.c.provider == provider,
                        user_identities_table.c.provider_user_id == provider_user_id,
                    )
                    .values(**identity_update_values)
                )
            return existing_user

        user_insert = (
            insert(users_table)
            .values(
                display_name=display_name or "未命名使用者",
                email=provider_email,
                avatar_url=avatar_url,
                locale=locale,
                timezone=timezone,
                base_currency=base_currency,
            )
            .returning(users_table)
        )
        new_user = self.db_session.execute(user_insert).first()
        user_data = dict(new_user._mapping)

        self.db_session.execute(
            insert(user_identities_table).values(
                user_id=user_data["id"],
                provider=provider,
                provider_user_id=provider_user_id,
                provider_email=provider_email,
                provider_display_name=display_name,
            )
        )
        return user_data

    def get_or_create_user(self, user_id, display_name=None):
        """相容舊呼叫點：將傳入的 user_id 視為 LINE provider user id。

        新功能請改用 get_or_create_user_for_identity。

        Args:
            user_id (str): 使用者的 Line User ID。
            display_name (str, optional): 使用者的 Line 顯示名稱。

        Returns:
            dict: 使用者資料。
        """
        return self.get_or_create_user_for_identity("line", user_id, display_name)
