from datetime import datetime
from sqlalchemy import select, func

from config import DEFAULT_CURRENCY
from .database import engine as global_engine # Rename to avoid conflict
from .schema import assets_table

class AssetManager:
    """管理資產，所有操作直接對資料庫進行。"""

    def __init__(self, engine=None):
        self.engine = engine or global_engine

    def _get_account_key(self, bank_name, account_type):
        """生成唯一的帳戶 key，用於內部存取"""
        return f"{bank_name}-{account_type}"

    def get_all_assets(self, user_id):
        """從資料庫獲取指定使用者的所有資產"""
        stmt = select(assets_table).where(assets_table.c.user_id == user_id)
        with self.engine.connect() as conn:
            result = conn.execute(stmt)
            assets = {row.account_key: dict(row._mapping) for row in result}
            return assets

    def find_asset_by_name(self, user_id, name):
        """根據自然語言名稱尋找指定使用者的資產。

        Args:
            user_id (str): 使用者 ID
            name (str): 欲尋找的資產名稱 (例如: 國泰銀行, 現金)

        Returns:
            dict or None: 找到的資產資料，或 None
        """
        # 未來可擴展模糊比對 (e.g., a LIKE query or a library like fuzzywuzzy)
        stmt = select(assets_table).where(assets_table.c.user_id == user_id, assets_table.c.bank_name == name)
        with self.engine.connect() as conn:
            result = conn.execute(stmt).first()
            if result:
                return dict(result._mapping)
        return None

    def add_account(self, user_id, bank_name, account_type, balance):
        """新增銀行帳戶到資料庫，並與使用者綁定"""
        account_key = self._get_account_key(bank_name, account_type)
        stmt = assets_table.insert().values(
            user_id=user_id,
            account_key=account_key,
            bank_name=bank_name,
            account_type=account_type,
            balance=balance,
            last_update=datetime.now(),
            currency=DEFAULT_CURRENCY
        )
        with self.engine.connect() as conn:
            try:
                conn.execute(stmt)
                conn.commit()
                print(f"✅ 已新增 {bank_name} {account_type} 到資料庫")
                return True, "成功新增帳戶"
            except Exception as e:
                print(f"❌ 新增帳戶失敗: {e}")
                return False, "新增帳戶失敗，帳戶可能已存在。"

    def adjust_asset_balance(self, user_id, account_key, amount_change):
        """調整指定帳戶的餘額 (可正可負)，並驗證使用者"""
        stmt = (
            assets_table.update()
            .where(assets_table.c.user_id == user_id, assets_table.c.account_key == account_key)
            .values(balance=assets_table.c.balance + amount_change, last_update=datetime.now())
        )
        with self.engine.connect() as conn:
            result = conn.execute(stmt)
            conn.commit()
            if result.rowcount == 0:
                print(f"❌ 調整餘額失敗: 找不到帳戶 {account_key} 或權限不足")
                return False, "找不到此帳戶"
            print(f"🔄 已調整帳戶 {account_key} 的餘額 {amount_change:+,}")
            return True, "餘額調整成功"

    def update_balance(self, user_id, account_key, new_balance):
        """更新指定帳戶的餘額，並驗證使用者"""
        if new_balance < 0:
            return False, "餘額不能為負數"
        stmt = (
            assets_table.update()
            .where(assets_table.c.user_id == user_id, assets_table.c.account_key == account_key)
            .values(balance=new_balance, last_update=datetime.now())
        )
        with self.engine.connect() as conn:
            result = conn.execute(stmt)
            conn.commit()
            if result.rowcount == 0:
                print(f"❌ 更新失敗: 找不到帳戶 {account_key} 或權限不足")
                return False, "找不到此帳戶"
            print(f"🔄 已更新帳戶 {account_key} 的餘額")
            return True, "餘額更新成功"

    def delete_account(self, user_id, account_key):
        """從資料庫刪除帳戶，並驗證使用者"""
        stmt = assets_table.delete().where(assets_table.c.user_id == user_id, assets_table.c.account_key == account_key)
        with self.engine.connect() as conn:
            result = conn.execute(stmt)
            conn.commit()
            if result.rowcount == 0:
                print(f"❌ 刪除失敗: 找不到帳戶 {account_key} 或權限不足")
                return False, "找不到要刪除的帳戶"
            print(f"🗑️ 已從資料庫刪除帳戶 {account_key}")
            return True, "成功刪除帳戶"

    def transfer(self, user_id, source_key, dest_key, amount):
        """處理帳戶間轉帳，使用資料庫 transaction 確保原子性並驗證使用者"""
        if amount <= 0:
            return False, "轉帳金額必須大於0"
        with self.engine.connect() as conn:
            with conn.begin() as transaction:
                try:
                    # 驗證來源帳戶屬於該使用者並取得其餘額
                    balance_stmt = select(assets_table.c.balance).where(
                        assets_table.c.user_id == user_id, 
                        assets_table.c.account_key == source_key
                    )
                    source_balance = conn.execute(balance_stmt).scalar_one_or_none()
                    if source_balance is None:
                        transaction.rollback()
                        return False, "來源帳戶不存在或權限不足"
                    if source_balance < amount:
                        transaction.rollback()
                        return False, "來源帳戶餘額不足"
                    
                    # 更新來源帳戶
                    update_source_stmt = (
                        assets_table.update()
                        .where(assets_table.c.user_id == user_id, assets_table.c.account_key == source_key)
                        .values(balance=assets_table.c.balance - amount, last_update=datetime.now())
                    )
                    conn.execute(update_source_stmt)
                    
                    # 更新目標帳戶
                    update_dest_stmt = (
                        assets_table.update()
                        .where(assets_table.c.user_id == user_id, assets_table.c.account_key == dest_key)
                        .values(balance=assets_table.c.balance + amount, last_update=datetime.now())
                    )
                    result = conn.execute(update_dest_stmt)
                    
                    # 如果目標帳戶更新沒有成功 (可能不存在或不屬於該使用者)，則回滾
                    if result.rowcount == 0:
                        transaction.rollback()
                        return False, "目標帳戶不存在或權限不足"
                        
                    print(f"✅ 成功從 {source_key} 轉帳 ${amount:,} 至 {dest_key}")
                    return True, "轉帳成功"
                except Exception as e:
                    transaction.rollback() # 確保出錯時回滾
                    print(f"❌ 轉帳過程中發生錯誤: {e}")
                    return False, "轉帳過程中發生錯誤"

    def calculate_totals(self, user_id):
        """使用 SQL 查詢計算指定使用者的各種總額"""
        stmt = select(
            assets_table.c.account_type,
            func.sum(assets_table.c.balance).label('total_balance')
        ).where(assets_table.c.user_id == user_id).group_by(assets_table.c.account_type)

        with self.engine.connect() as conn:
            result = conn.execute(stmt)
            
            # 初始化結果
            totals = {"總資產": 0, "活存": 0, "定存": 0, "投資": 0, "信用卡": 0, "其他": 0}
            for row in result:
                balance = float(row.total_balance)
                totals["總資產"] += balance
                if row.account_type in totals:
                    totals[row.account_type] += balance
                else:
                    totals["其他"] += balance
            return totals