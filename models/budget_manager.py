from datetime import datetime
import uuid
from sqlalchemy import select, insert, update, delete, func, distinct
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .database import engine as global_engine # Rename to avoid conflict
from .schema import transactions_table, budget_months_table, budget_categories_table

class BudgetManager:
    """管理預算與交易，所有操作直接對資料庫進行。"""

    def __init__(self, engine=None):
        self.engine = engine or global_engine

    # --- Transaction Methods ---

    def get_all_transactions(self, user_id=None):
        """獲取指定使用者的所有交易紀錄"""
        if not user_id:
            return []
        stmt = select(transactions_table).where(transactions_table.c.user_id == user_id).order_by(transactions_table.c.date.desc())
        with self.engine.connect() as conn:
            result = conn.execute(stmt)
            transactions = []
            for row in result:
                transaction = dict(row._mapping)
                # Ensure date is formatted as YYYY-MM-DD string
                if isinstance(transaction['date'], datetime):
                    transaction['date'] = transaction['date'].strftime('%Y-%m-%d')
                transactions.append(transaction)
            return transactions

    def add_transaction(self, user_id, date, item, amount, transaction_type, budget_category, description=""):
        """新增一筆交易紀錄，並綁定使用者"""
        if not user_id:
            return False, "使用者ID未提供"
        if amount <= 0:
            return False, "金額必須大於0"

        stmt = insert(transactions_table).values(
            id=uuid.uuid4(),
            user_id=user_id,
            date=date,
            type=transaction_type,
            category=item,
            budget_category=budget_category,
            amount=amount,
            description=description,
            timestamp=datetime.now()
        )
        with self.engine.connect() as conn:
            try:
                conn.execute(stmt)
                conn.commit()
                return True, "交易新增成功"
            except Exception as e:
                return False, f"新增交易失敗: {e}"

    def delete_transaction(self, user_id, transaction_id):
        """刪除一筆交易，並驗證使用者"""
        if not user_id:
            return False, "使用者ID未提供"
        stmt = delete(transactions_table).where(
            transactions_table.c.id == transaction_id,
            transactions_table.c.user_id == user_id
        )
        with self.engine.connect() as conn:
            result = conn.execute(stmt)
            conn.commit()
            if result.rowcount == 0:
                return False, "找不到要刪除的交易或權限不足"
            return True, "交易刪除成功"

    def get_all_transaction_months(self, user_id=None):
        """從指定使用者的交易紀錄中提取所有唯一的月份 (YYYY-MM)"""
        if not user_id:
            return []
        month_expr = func.to_char(transactions_table.c.date, 'YYYY-MM')
        stmt = select(distinct(month_expr)).where(transactions_table.c.user_id == user_id).order_by(month_expr.desc())
        with self.engine.connect() as conn:
            result = conn.execute(stmt)
            return [row[0] for row in result]

    # --- Budget Methods ---

    def set_budget(self, user_id, month, category, amount, notes=""):
        """設定某位使用者在某月某類別的預算 (使用 Upsert 邏輯)"""
        if not user_id:
            return False, "使用者ID未提供"
        if amount <= 0:
            return False, "預算金額必須大於0"

        with self.engine.connect() as conn:
            with conn.begin() as transaction: # Start transaction
                try:
                    # 1. 確保月份存在於 budget_months (for this user)
                    month_stmt = pg_insert(budget_months_table).values(
                        user_id=user_id,
                        month=month,
                        created_date=datetime.now()
                    ).on_conflict_do_nothing() # Composite PK handles conflict
                    conn.execute(month_stmt)

                    # 2. Upsert 預算類別
                    category_stmt = pg_insert(budget_categories_table).values(
                        user_id=user_id,
                        month=month,
                        category_name=category,
                        amount=amount,
                        notes=notes,
                        created_date=datetime.now()
                    )
                    # 如果 user_id, 月份和類別名稱衝突，則更新金額和備註
                    upsert_stmt = category_stmt.on_conflict_on_constraint('uq_user_month_category').do_update(
                        set_=dict(amount=category_stmt.excluded.amount, notes=category_stmt.excluded.notes)
                    )
                    conn.execute(upsert_stmt)
                    
                    return True, "預算設定成功"
                except Exception as e:
                    import traceback
                    print(f"詳細錯誤: {traceback.format_exc()}")
                    return False, f"詳細錯誤: {type(e).__name__} -> {str(e)}"

    def delete_budget(self, user_id, month, category):
        """刪除某位使用者在某月某類別的預算"""
        if not user_id:
            return False, "使用者ID未提供"
        stmt = delete(budget_categories_table).where(
            budget_categories_table.c.user_id == user_id,
            budget_categories_table.c.month == month,
            budget_categories_table.c.category_name == category
        )
        with self.engine.connect() as conn:
            result = conn.execute(stmt)
            conn.commit()
            if result.rowcount == 0:
                return False, "找不到要刪除的預算或權限不足"
            return True, "預算刪除成功"

    def get_all_budget_categories(self, user_id=None):
        """獲取指定使用者所有已設定預算的類別"""
        if not user_id:
            return []
        # 從預算類別表和交易表中都獲取，確保完整性
        stmt1 = select(distinct(budget_categories_table.c.category_name)).where(budget_categories_table.c.user_id == user_id)
        stmt2 = select(distinct(transactions_table.c.budget_category)).where(
            transactions_table.c.user_id == user_id,
            transactions_table.c.budget_category.isnot(None)
        )
        
        categories = set()
        with self.engine.connect() as conn:
            result1 = conn.execute(stmt1)
            for row in result1:
                categories.add(row[0])
            result2 = conn.execute(stmt2)
            for row in result2:
                categories.add(row[0])
        return sorted(list(categories))

    # --- Calculation Methods ---

    def calculate_monthly_expenses(self, user_id, year_month):
        """使用 SQL彙總指定使用者在某月的支出"""
        if not user_id:
            return {}
        stmt = (
            select(transactions_table.c.budget_category, func.sum(transactions_table.c.amount).label("total_spent"))
            .where(transactions_table.c.user_id == user_id)
            .where(transactions_table.c.type == 'expense')
            .where(func.to_char(transactions_table.c.date, 'YYYY-MM') == year_month)
            .group_by(transactions_table.c.budget_category)
        )
        with self.engine.connect() as conn:
            result = conn.execute(stmt)
            return {row.budget_category: row.total_spent for row in result}

    def get_transactions_by_category_over_time(self, user_id, interval='month'):
        """按時間間隔和類別匯總指定使用者的支出數據"""
        if not user_id:
            return {"labels": [], "datasets": []}
        if interval == 'month':
            time_format = 'YYYY-MM'
        elif interval == 'year':
            time_format = 'YYYY'
        else: # Default to month if interval is invalid
            time_format = 'YYYY-MM'

        time_period = func.to_char(transactions_table.c.date, time_format).label('time_period')
        
        stmt = (
            select(
                time_period,
                transactions_table.c.budget_category,
                func.sum(transactions_table.c.amount).label("total_spent")
            )
            .where(transactions_table.c.user_id == user_id)
            .where(transactions_table.c.type == 'expense')
            .where(transactions_table.c.budget_category.isnot(None))
            .group_by(time_period, transactions_table.c.budget_category)
            .order_by(time_period.asc(), transactions_table.c.budget_category.asc())
        )

        with self.engine.connect() as conn:
            result = conn.execute(stmt)
            # Restructure data for charting
            data = {} # { '2023-01': {'Food': 100, 'Transport': 50}, ... }
            for row in result:
                period = row.time_period
                category = row.budget_category
                spent = float(row.total_spent)
                
                if period not in data:
                    data[period] = {}
                data[period][category] = spent

        if not data:
            return {"labels": [], "datasets": []}

        # Final transformation for Chart.js
        labels = sorted(list(data.keys()))
        all_categories = sorted(list(set(cat for period_data in data.values() for cat in period_data.keys())))
        
        datasets = []
        # A color palette for the chart
        colors = ["#42A5F5", "#66BB6A", "#FFA726", "#26A69A", "#BDBDBD", "#7986CB", "#C0CA33", "#FF7043", "#8D6E63", "#EC407A"]
        
        for i, category in enumerate(all_categories):
            dataset = {
                "label": category,
                "data": [data[label].get(category, 0) for label in labels],
                "backgroundColor": colors[i % len(colors)],
            }
            datasets.append(dataset)
            
        return {"labels": labels, "datasets": datasets}

    def check_over_warnings(self, user_id, month=None):
        """檢查指定使用者的超支警告"""
        if not user_id:
            return []
        overspend_items = []
        # 1. 獲取指定使用者的所有預算
        budget_stmt = select(budget_categories_table).where(budget_categories_table.c.user_id == user_id)
        if month:
            budget_stmt = budget_stmt.where(budget_categories_table.c.month == month)
        
        with self.engine.connect() as conn:
            budgets_result = conn.execute(budget_stmt)
            all_budgets = {(row.month, row.category_name): row.amount for row in budgets_result}

        # 2. 獲取所有相關月份的支出
        months_to_check = {b[0] for b in all_budgets.keys()}
        if not months_to_check:
            return []

        expense_stmt = (
            select(
                func.to_char(transactions_table.c.date, 'YYYY-MM').label("month"),
                transactions_table.c.budget_category,
                func.sum(transactions_table.c.amount).label("total_spent")
            )
            .where(transactions_table.c.user_id == user_id)
            .where(transactions_table.c.type == 'expense')
            .where(func.to_char(transactions_table.c.date, 'YYYY-MM').in_(months_to_check))
            .group_by("month", transactions_table.c.budget_category)
        )
        with self.engine.connect() as conn:
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
