# models/asset_manager.py

from datetime import datetime
from decimal import Decimal
from sqlalchemy import select, func, update, delete, insert

from config import DEFAULT_CURRENCY
from .schema import assets_table

class AssetManager:
    """管理資產，所有操作都透過傳入的 db_session 進行。"""

    def _get_account_key(self, bank_name, account_type):
        """生成唯一的帳戶 key，用於內部存取"""
        return f"{bank_name}-{account_type}"

    def get_all_assets(self, db_session, user_id):
        """從資料庫獲取指定使用者的所有資產"""
        stmt = select(assets_table).where(assets_table.c.user_id == user_id)
        result = db_session.execute(stmt)
        assets = {row.account_key: dict(row._mapping) for row in result}
        return assets

    def find_asset_by_name(self, db_session, user_id, name):
        """根據自然語言名稱尋找指定使用者的資產。"""
        stmt = select(assets_table).where(
            assets_table.c.user_id == user_id, 
            func.lower(assets_table.c.bank_name) == name.lower()
        )
        result = db_session.execute(stmt).first()
        if result:
            return dict(result._mapping)
        return None

    def add_account(self, db_session, user_id, bank_name, account_type, balance):
        """新增銀行帳戶到資料庫，並與使用者綁定"""
        account_key = self._get_account_key(bank_name, account_type)
        stmt = insert(assets_table).values(
            user_id=user_id,
            account_key=account_key,
            bank_name=bank_name,
            account_type=account_type,
            balance=balance,
            last_update=datetime.now(),
            currency=DEFAULT_CURRENCY
        )
        try:
            db_session.execute(stmt)
            print(f"✅ 已新增 {bank_name} {account_type} 到資料庫")
            return True, "成功新增帳戶"
        except Exception as e:
            # 讓外層的 session manager 處理 rollback
            raise e

    def adjust_asset_balance(self, db_session, user_id, account_key, amount_change):
        """調整指定帳戶的餘額 (可正可負)，並驗證使用者"""
        stmt = (
            update(assets_table)
            .where(assets_table.c.user_id == user_id, assets_table.c.account_key == account_key)
            .values(balance=assets_table.c.balance + Decimal(str(amount_change)), last_update=datetime.now())
        )
        result = db_session.execute(stmt)
        if result.rowcount == 0:
            # 拋出錯誤，讓外層 rollback
            raise ValueError("找不到此帳戶或權限不足")
        print(f"🔄 已調整帳戶 {account_key} 的餘額 {amount_change:+,}")
        return True, "餘額調整成功"

    def update_balance(self, db_session, user_id, account_key, new_balance):
        """更新指定帳戶的餘額，並驗證使用者"""
        if new_balance < 0:
            return False, "餘額不能為負數"
        stmt = (
            update(assets_table)
            .where(assets_table.c.user_id == user_id, assets_table.c.account_key == account_key)
            .values(balance=new_balance, last_update=datetime.now())
        )
        result = db_session.execute(stmt)
        if result.rowcount == 0:
            raise ValueError("找不到此帳戶或權限不足")
        print(f"🔄 已更新帳戶 {account_key} 的餘額")
        return True, "餘額更新成功"

    def delete_account(self, db_session, user_id, account_key):
        """從資料庫刪除帳戶，並驗證使用者"""
        stmt = delete(assets_table).where(assets_table.c.user_id == user_id, assets_table.c.account_key == account_key)
        result = db_session.execute(stmt)
        if result.rowcount == 0:
            raise ValueError("找不到要刪除的帳戶或權限不足")
        print(f"🗑️ 已從資料庫刪除帳戶 {account_key}")
        return True, "成功刪除帳戶"

    def transfer(self, db_session, user_id, source_key, dest_key, amount):
        """處理帳戶間轉帳。交易由外部的 session manager 控制。""" 
        if amount <= 0:
            return False, "轉帳金額必須大於0"
        
        # 1. 驗證來源帳戶餘額
        balance_stmt = select(assets_table.c.balance).where(
            assets_table.c.user_id == user_id, 
            assets_table.c.account_key == source_key
        )
        source_balance = db_session.execute(balance_stmt).scalar_one_or_none()
        
        if source_balance is None:
            raise ValueError("來源帳戶不存在或權限不足")
        if source_balance < amount:
            raise ValueError("來源帳戶餘額不足")
        
        # 2. 更新來源帳戶
        update_source_stmt = (
            update(assets_table)
            .where(assets_table.c.user_id == user_id, assets_table.c.account_key == source_key)
            .values(balance=assets_table.c.balance - Decimal(str(amount)), last_update=datetime.now())
        )
        db_session.execute(update_source_stmt)
        
        # 3. 更新目標帳戶
        update_dest_stmt = (
            update(assets_table)
            .where(assets_table.c.user_id == user_id, assets_table.c.account_key == dest_key)
            .values(balance=assets_table.c.balance + Decimal(str(amount)), last_update=datetime.now())
        )
        result = db_session.execute(update_dest_stmt)
        
        # 4. 如果目標帳戶更新失敗，拋出異常，觸發 rollback
        if result.rowcount == 0:
            raise ValueError("目標帳戶不存在或權限不足")
            
        print(f"✅ 成功從 {source_key} 轉帳 ${amount:,} 至 {dest_key}")
        return True, "轉帳成功"

    def calculate_totals(self, db_session, user_id):
        """使用 SQL 查詢計算指定使用者的各種總額"""
        totals = {"總資產": 0, "活存": 0, "定存": 0, "投資": 0, "信用卡": 0, "其他": 0}
        
        stmt = select(
            assets_table.c.account_type,
            func.sum(assets_table.c.balance).label('total_balance')
        ).where(assets_table.c.user_id == user_id).group_by(assets_table.c.account_type)

        result = db_session.execute(stmt)
        
        for row in result:
            balance = float(row.total_balance)
            totals["總資產"] += balance
            if row.account_type in totals:
                totals[row.account_type] += balance
            else:
                totals["其他"] += balance
        return totals