# models/budget_manager.py

from datetime import datetime
import uuid
from sqlalchemy import select, insert, update, delete, func, distinct
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .schema import transactions_table, budget_months_table, budget_categories_table

class BudgetManager:
    """管理預算與交易，所有操作都透過傳入的 db_session 進行。"""
    def __init__(self, db_session):
        self.db_session = db_session

    # --- Transaction Methods ---

    def get_all_transactions(self, user_id):
        """獲取指定使用者的所有交易紀錄"""
        stmt = select(transactions_table).where(transactions_table.c.user_id == user_id).order_by(transactions_table.c.date.desc())
        result = self.db_session.execute(stmt)
        transactions = []
        for row in result:
            transaction = dict(row._mapping)
            if isinstance(transaction.get('date'), datetime):
                transaction['date'] = transaction['date'].strftime('%Y-%m-%d')
            transactions.append(transaction)
        return transactions

    def add_transaction(self, user_id, date, item, amount, transaction_type, budget_category, description=""):
        """新增一筆交易紀錄，並綁定使用者"""
        if amount <= 0:
            raise ValueError("金額必須大於0")

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
        self.db_session.execute(stmt)
        return True, "交易新增成功"

    def delete_transaction(self, user_id, transaction_id):
        """刪除一筆交易，並驗證使用者"""
        stmt = delete(transactions_table).where(
            transactions_table.c.id == transaction_id,
            transactions_table.c.user_id == user_id
        )
        result = self.db_session.execute(stmt)
        if result.rowcount == 0:
            raise ValueError("找不到要刪除的交易或權限不足")
        return True, "交易刪除成功"

    def get_all_transaction_months(self, user_id):
        """從指定使用者的交易紀錄中提取所有唯一的月份 (YYYY-MM)"""
        month_expr = func.to_char(transactions_table.c.date, 'YYYY-MM')
        stmt = select(distinct(month_expr)).where(transactions_table.c.user_id == user_id).order_by(month_expr.desc())
        result = self.db_session.execute(stmt)
        return [row[0] for row in result]

    # --- Budget Methods ---

    def set_budget(self, user_id, month, category, amount, notes=""):
        """設定某位使用者在某月某類別的預算 (使用 Upsert 邏輯)"""
        if amount <= 0:
            raise ValueError("預算金額必須大於0")

        # 1. 確保月份存在於 budget_months (for this user)
        month_stmt = pg_insert(budget_months_table).values(
            user_id=user_id,
            month=month,
            created_date=datetime.now()
        ).on_conflict_do_nothing()
        self.db_session.execute(month_stmt)

        # 2. Upsert 預算類別
        category_stmt = pg_insert(budget_categories_table).values(
            user_id=user_id,
            month=month,
            category_name=category,
            amount=amount,
            notes=notes,
            created_date=datetime.now()
        )
        upsert_stmt = category_stmt.on_conflict_do_update(
            index_elements=['user_id', 'month', 'category_name'],
            set_=dict(amount=category_stmt.excluded.amount, notes=category_stmt.excluded.notes)
        )
        self.db_session.execute(upsert_stmt)
        
        return True, "預算設定成功"

    def delete_budget(self, user_id, month, category):
        """刪除某位使用者在某月某類別的預算"""
        stmt = delete(budget_categories_table).where(
            budget_categories_table.c.user_id == user_id,
            budget_categories_table.c.month == month,
            budget_categories_table.c.category_name == category
        )
        result = self.db_session.execute(stmt)
        if result.rowcount == 0:
            raise ValueError("找不到要刪除的預算或權限不足")
        return True, "預算刪除成功"

    def get_all_budget_categories(self, user_id):
        """獲取指定使用者所有已設定預算的類別"""
        stmt1 = select(distinct(budget_categories_table.c.category_name)).where(budget_categories_table.c.user_id == user_id)
        stmt2 = select(distinct(transactions_table.c.budget_category)).where(
            transactions_table.c.user_id == user_id,
            transactions_table.c.budget_category.isnot(None)
        )
        
        categories = set()
        result1 = self.db_session.execute(stmt1)
        for row in result1:
            categories.add(row[0])
        result2 = self.db_session.execute(stmt2)
        for row in result2:
            categories.add(row[0])
        return sorted(list(categories))

    # --- Calculation Methods ---

    def calculate_monthly_expenses(self, user_id, year_month):
        """使用 SQL彙總指定使用者在某月的支出"""
        stmt = (
            select(transactions_table.c.budget_category, func.sum(transactions_table.c.amount).label("total_spent"))
            .where(transactions_table.c.user_id == user_id)
            .where(transactions_table.c.type == 'expense')
            .where(func.to_char(transactions_table.c.date, 'YYYY-MM') == year_month)
            .group_by(transactions_table.c.budget_category)
        )
        result = self.db_session.execute(stmt)
        return {row.budget_category: row.total_spent for row in result}

    def get_transactions_by_category_over_time(self, user_id, interval='month'):
        """按時間間隔和類別匯總指定使用者的支出數據"""
        time_format = 'YYYY-MM' if interval == 'month' else 'YYYY'
        time_period = func.to_char(transactions_table.c.date, time_format).label('time_period')
        
        stmt = (
            select(
                time_period,
                transactions_table.c.budget_category,
                func.sum(transactions_table.c.amount).label("total_spent")
            )
            .where(transactions_table.c.user_id == user_id, transactions_table.c.type == 'expense', transactions_table.c.budget_category.isnot(None))
            .group_by(time_period, transactions_table.c.budget_category)
            .order_by(time_period.asc(), transactions_table.c.budget_category.asc())
        )

        result = self.db_session.execute(stmt)
        data = {}
        for row in result:
            period, category, spent = row.time_period, row.budget_category, float(row.total_spent)
            if period not in data:
                data[period] = {}
            data[period][category] = spent

        if not data:
            return {"labels": [], "datasets": []}

        labels = sorted(data.keys())
        all_categories = sorted({cat for period_data in data.values() for cat in period_data})
        colors = ["#42A5F5", "#66BB6A", "#FFA726", "#26A69A", "#BDBDBD", "#7986CB", "#C0CA33", "#FF7043", "#8D6E63", "#EC407A"]
        
        datasets = [
            {
                "label": category,
                "data": [data[label].get(category, 0) for label in labels],
                "backgroundColor": colors[i % len(colors)],
            }
            for i, category in enumerate(all_categories)
        ]
            
        return {"labels": labels, "datasets": datasets}

    def check_over_warnings(self, user_id, month=None):
        """檢查指定使用者的超支警告"""
        budget_stmt = select(budget_categories_table).where(budget_categories_table.c.user_id == user_id)
        if month:
            budget_stmt = budget_stmt.where(budget_categories_table.c.month == month)
        
        budgets_result = self.db_session.execute(budget_stmt)
        all_budgets = {(row.month, row.category_name): row.amount for row in budgets_result}

        months_to_check = {b[0] for b in all_budgets.keys()}
        if not months_to_check:
            return []

        expense_stmt = (
            select(
                func.to_char(transactions_table.c.date, 'YYYY-MM').label("month"),
                transactions_table.c.budget_category,
                func.sum(transactions_table.c.amount).label("total_spent")
            )
            .where(transactions_table.c.user_id == user_id, transactions_table.c.type == 'expense', func.to_char(transactions_table.c.date, 'YYYY-MM').in_(months_to_check))
            .group_by("month", transactions_table.c.budget_category)
        )
        expenses_result = self.db_session.execute(expense_stmt)
        all_expenses = {(row.month, row.budget_category): row.total_spent for row in expenses_result}

        return [
            {
                "month": b_month,
                "category": b_category,
                "budget": budget_amount,
                "spent": spent_amount,
                "overspend": spent_amount - budget_amount,
            }
            for (b_month, b_category), budget_amount in all_budgets.items()
            if (spent_amount := all_expenses.get((b_month, b_category), 0)) > budget_amount
        ]