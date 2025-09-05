from datetime import datetime
import uuid
from sqlalchemy import select, insert, update, delete, func, distinct
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .database import engine
from .schema import transactions_table, budget_months_table, budget_categories_table

class BudgetManager:
    """管理預算與交易，所有操作直接對資料庫進行。"""

    # --- Transaction Methods ---

    def get_all_transactions(self):
        """獲取所有交易紀錄"""
        stmt = select(transactions_table).order_by(transactions_table.c.date.desc())
        with engine.connect() as conn:
            result = conn.execute(stmt)
            return [dict(row._mapping) for row in result]

    def add_transaction(self, date, item, amount, transaction_type, budget_category, description=""):
        """新增一筆交易紀錄"""
        if amount <= 0:
            return False, "金額必須大於0"

        stmt = insert(transactions_table).values(
            id=uuid.uuid4(),
            date=date,
            type=transaction_type,
            category=item,
            budget_category=budget_category,
            amount=amount,
            description=description,
            timestamp=datetime.now()
        )
        with engine.connect() as conn:
            try:
                conn.execute(stmt)
                conn.commit()
                return True, "交易新增成功"
            except Exception as e:
                return False, f"新增交易失敗: {e}"

    def delete_transaction(self, transaction_id):
        """刪除一筆交易"""
        stmt = delete(transactions_table).where(transactions_table.c.id == transaction_id)
        with engine.connect() as conn:
            result = conn.execute(stmt)
            conn.commit()
            if result.rowcount == 0:
                return False, "找不到要刪除的交易"
            return True, "交易刪除成功"

    def get_all_transaction_months(self):
        """從交易紀錄中提取所有唯一的月份 (YYYY-MM)"""
        month_expr = func.to_char(transactions_table.c.date, 'YYYY-MM')
        stmt = select(distinct(month_expr)).order_by(month_expr.desc())
        with engine.connect() as conn:
            result = conn.execute(stmt)
            return [row[0] for row in result]

    # --- Budget Methods ---

    def set_budget(self, month, category, amount, notes=""):
        """設定某月某類別的預算 (使用 Upsert 邏輯)"""
        if amount <= 0:
            return False, "預算金額必須大於0"

        with engine.connect() as conn:
            with conn.begin() as transaction: # Start transaction
                try:
                    # 1. 確保月份存在於 budget_months
                    month_stmt = pg_insert(budget_months_table).values(
                        month=month,
                        created_date=datetime.now()
                    ).on_conflict_do_nothing()
                    conn.execute(month_stmt)

                    # 2. Upsert 預算類別
                    category_stmt = pg_insert(budget_categories_table).values(
                        month=month,
                        category_name=category,
                        amount=amount,
                        notes=notes,
                        created_date=datetime.now()
                    )
                    # 如果月份和類別名稱衝突，則更新金額和備註
                    upsert_stmt = category_stmt.on_conflict_on_constraint('uq_month_category').do_update(
                        set_=dict(amount=category_stmt.excluded.amount, notes=category_stmt.excluded.notes)
                    )
                    conn.execute(upsert_stmt)
                    
                    return True, "預算設定成功"
                except Exception as e:
                    return False, f"設定預算時發生錯誤: {e}"

    def delete_budget(self, month, category):
        """刪除某月某類別的預算"""
        stmt = delete(budget_categories_table).where(
            budget_categories_table.c.month == month,
            budget_categories_table.c.category_name == category
        )
        with engine.connect() as conn:
            result = conn.execute(stmt)
            conn.commit()
            if result.rowcount == 0:
                return False, "找不到要刪除的預算"
            return True, "預算刪除成功"

    def get_all_budget_categories(self):
        """獲取所有已設定預算的類別"""
        # 從預算類別表和交易表中都獲取，確保完整性
        stmt1 = select(distinct(budget_categories_table.c.category_name))
        stmt2 = select(distinct(transactions_table.c.budget_category)).where(transactions_table.c.budget_category.isnot(None))
        
        categories = set()
        with engine.connect() as conn:
            result1 = conn.execute(stmt1)
            for row in result1:
                categories.add(row[0])
            result2 = conn.execute(stmt2)
            for row in result2:
                categories.add(row[0])
        return sorted(list(categories))

    # --- Calculation Methods ---

    def calculate_monthly_expenses(self, year_month):
        """使用 SQL彙總每月支出"""
        stmt = (
            select(transactions_table.c.budget_category, func.sum(transactions_table.c.amount).label("total_spent"))
            .where(transactions_table.c.type == 'expense')
            .where(func.to_char(transactions_table.c.date, 'YYYY-MM') == year_month)
            .group_by(transactions_table.c.budget_category)
        )
        with engine.connect() as conn:
            result = conn.execute(stmt)
            return {row.budget_category: row.total_spent for row in result}

    def check_over_warnings(self, month=None):
        """檢查超支警告"""
        overspend_items = []
        # 1. 獲取所有預算
        budget_stmt = select(budget_categories_table)
        if month:
            budget_stmt = budget_stmt.where(budget_categories_table.c.month == month)
        
        with engine.connect() as conn:
            budgets_result = conn.execute(budget_stmt)
            all_budgets = {(row.month, row.category_name): row.amount for row in budgets_result}

        # 2. 獲取所有月份的支出
        months_to_check = {b[0] for b in all_budgets.keys()}
        if not months_to_check:
            return []

        expense_stmt = (
            select(
                func.to_char(transactions_table.c.date, 'YYYY-MM').label("month"),
                transactions_table.c.budget_category,
                func.sum(transactions_table.c.amount).label("total_spent")
            )
            .where(transactions_table.c.type == 'expense')
            .where(func.to_char(transactions_table.c.date, 'YYYY-MM').in_(months_to_check))
            .group_by("month", transactions_table.c.budget_category)
        )
        with engine.connect() as conn:
            expenses_result = conn.execute(expense_stmt)
            all_expenses = {(row.month, row.budget_category): row.total_spent for row in expenses_result}

        # 3. 在 Python 中比較
        for (b_month, b_category), budget_amount in all_budgets.items():
            spent_amount = all_expenses.get((b_month, b_category), 0)
            if spent_amount > budget_amount:
                overspend_items.append({
                    "month": b_month,
                    "category": b_category,
                    "budget": budget_amount,
                    "spent": spent_amount,
                    "overspend": spent_amount - budget_amount,
                })
        return overspend_items
