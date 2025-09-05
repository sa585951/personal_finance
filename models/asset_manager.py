from datetime import datetime
from sqlalchemy import select, func

from config import DEFAULT_CURRENCY
from .database import engine
from .schema import assets_table

class AssetManager:
    """管理資產，所有操作直接對資料庫進行。"""

    def _get_account_key(self, bank_name, account_type):
        """生成唯一的帳戶 key，用於內部存取"""
        return f"{bank_name}-{account_type}"

    def get_all_assets(self):
        """從資料庫獲取所有資產"""
        stmt = select(assets_table)
        with engine.connect() as conn:
            result = conn.execute(stmt)
            assets = {row.account_key: dict(row._mapping) for row in result}
            return assets

    def add_account(self, bank_name, account_type, balance):
        """新增銀行帳戶到資料庫"""
        account_key = self._get_account_key(bank_name, account_type)
        stmt = assets_table.insert().values(
            account_key=account_key,
            bank_name=bank_name,
            account_type=account_type,
            balance=balance,
            last_update=datetime.now(),
            currency=DEFAULT_CURRENCY
        )
        with engine.connect() as conn:
            try:
                conn.execute(stmt)
                conn.commit()
                print(f"✅ 已新增 {bank_name} {account_type} 到資料庫")
                return True, "成功新增帳戶"
            except Exception as e:
                print(f"❌ 新增帳戶失敗: {e}")
                return False, "新增帳戶失敗，帳戶可能已存在。"

    def update_balance(self, account_key, new_balance):
        """更新指定帳戶的餘額"""
        if new_balance < 0:
            return False, "餘額不能為負數"
        stmt = (
            assets_table.update()
            .where(assets_table.c.account_key == account_key)
            .values(balance=new_balance, last_update=datetime.now())
        )
        with engine.connect() as conn:
            result = conn.execute(stmt)
            conn.commit()
            if result.rowcount == 0:
                print(f"❌ 更新失敗: 找不到帳戶 {account_key}")
                return False, "找不到此帳戶"
            print(f"🔄 已更新帳戶 {account_key} 的餘額")
            return True, "餘額更新成功"

    def delete_account(self, account_key):
        """從資料庫刪除帳戶"""
        stmt = assets_table.delete().where(assets_table.c.account_key == account_key)
        with engine.connect() as conn:
            result = conn.execute(stmt)
            conn.commit()
            if result.rowcount == 0:
                print(f"❌ 刪除失敗: 找不到帳戶 {account_key}")
                return False, "找不到要刪除的帳戶"
            print(f"🗑️ 已從資料庫刪除帳戶 {account_key}")
            return True, "成功刪除帳戶"

    def transfer(self, source_key, dest_key, amount):
        """處理帳戶間轉帳，使用資料庫 transaction 確保原子性"""
        if amount <= 0:
            return False, "轉帳金額必須大於0"
        with engine.connect() as conn:
            with conn.begin() as transaction:
                try:
                    balance_stmt = select(assets_table.c.balance).where(assets_table.c.account_key == source_key)
                    source_balance = conn.execute(balance_stmt).scalar_one_or_none()
                    if source_balance is None:
                        transaction.rollback()
                        return False, "來源帳戶不存在"
                    if source_balance < amount:
                        transaction.rollback()
                        return False, "來源帳戶餘額不足"
                    update_source_stmt = (
                        assets_table.update()
                        .where(assets_table.c.account_key == source_key)
                        .values(balance=assets_table.c.balance - amount, last_update=datetime.now())
                    )
                    conn.execute(update_source_stmt)
                    update_dest_stmt = (
                        assets_table.update()
                        .where(assets_table.c.account_key == dest_key)
                        .values(balance=assets_table.c.balance + amount, last_update=datetime.now())
                    )
                    result = conn.execute(update_dest_stmt)
                    if result.rowcount == 0:
                        transaction.rollback()
                        return False, "目標帳戶不存在"
                    print(f"✅ 成功從 {source_key} 轉帳 ${amount:,} 至 {dest_key}")
                    return True, "轉帳成功"
                except Exception as e:
                    print(f"❌ 轉帳過程中發生錯誤: {e}")
                    return False, "轉帳過程中發生錯誤"

    def calculate_totals(self):
        """使用 SQL 查詢計算各種總額"""
        stmt = select(
            assets_table.c.account_type,
            func.sum(assets_table.c.balance).label('total_balance')
        ).group_by(assets_table.c.account_type)

        with engine.connect() as conn:
            result = conn.execute(stmt)
            
            # 初始化結果
            totals = {"總資產": 0, "活存": 0, "定存": 0, "投資": 0, "其他": 0}
            for row in result:
                balance = float(row.total_balance)
                totals["總資產"] += balance
                if row.account_type in totals:
                    totals[row.account_type] += balance
                else:
                    totals["其他"] += balance
            return totals