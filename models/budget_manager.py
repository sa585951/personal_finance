import os
from datetime import datetime
from config import BUDGETS_FILE, TRANSACTIONS_FILE
from utils import load_json_file, save_json_file
import uuid

class BudgetManager:
    """
    管理預算與支出的核心邏輯。
    負責新增預算、記錄支出以及進行相關的純計算。
    """
    def __init__(self):
        self.budget_file = BUDGETS_FILE
        self.transaction_file = TRANSACTIONS_FILE  # 改個更清楚的名稱
        self.budgets = {}
        self.transactions = []  # 直接使用 transactions
        self.load_data()

    def load_data(self):
        """載入 Budget/expense 資料"""
        self.budgets = load_json_file(self.budget_file, {})
        self.transactions = load_json_file(self.transaction_file, [])
        if self.budgets:
            print(f"📖 載入現有預算: {len(self.budgets)} 個")
        else:
            print("🆕 建立新的預算")
        
        if self.transactions:
            print(f"📖 載入現有開銷: {len(self.transactions)} 個")
        else:
            print("🆕 建立新的交易紀錄")

    def save_data(self):
        """儲存資料"""
        saved_budgets = save_json_file(self.budget_file, self.budgets)
        saved_transactions = save_json_file(self.transaction_file, self.transactions)
        return saved_budgets and saved_transactions
    
    def get_all_budget_categories(self):
        """
        獲取所有已設定預算的類別
        """
        categories = set()

        # 從預算中獲取類別
        for month_data in self.budgets.values():
            for category in month_data.keys():
                categories.add(category)
        
        # 從交易中獲取類別
        for transaction in self.transactions:
            budget_category = transaction.get("budget_category")
            if budget_category:
                categories.add(budget_category)

        return sorted(list(categories))

    def set_budget(self, month, category, amount, notes=""):
        """設定某月某類別的預算"""
        if amount <= 0:
            return False

        if month not in self.budgets:
            self.budgets[month] = {}

        self.budgets[month][category] = {
            "amount": amount,
            "created_date": datetime.now().isoformat(),
            "notes": notes,
        }
        
        return self.save_data()
    
    def delete_budget(self, month, category):
        """刪除某月某類別的預算"""
        if month in self.budgets and category in self.budgets[month]:
            del self.budgets[month][category]
            if not self.budgets[month]:
                del self.budgets[month]

            if self.save_data():
                print(f"🗑️ 已刪除 {month} {category} 的預算")
                return True
            else:
                print("❌ 刪除預算失敗，無法儲存資料")
                return False
        else:
            print("❌ 找不到要刪除的預算")
            return False
        
    def get_all_transaction_months(self):
        """
        從交易紀錄中提取所有唯一的月份
        """
        months = set()
        for transaction in self.transactions:
            date_str = transaction.get("date")
            if date_str and len(date_str) >= 7:
                month = date_str[:7]  # 提取 'YYYY-MM' 部分
                months.add(month)
        return list(months)

    def add_transaction(self, date, item, amount, transaction_type, budget_category, description=""):
        """
        新增一筆交易紀錄
        :param date: 交易日期 (YYYY-MM-DD)
        :param item: 交易項目 (例如: 早餐)
        :param amount: 交易金額
        :param transaction_type: 交易類型 (expense 或 income)
        :param budget_category: 預算類別 (例如: 伙食)
        :param description: 備註
        """
        if amount <= 0:
            return False

        new_transaction = {
            "id": str(uuid.uuid4()),
            "date": date,
            "type": transaction_type,
            "category": item,  
            "budget_category": budget_category, 
            "amount": amount,
            "description": description,
            "timestamp": datetime.now().isoformat(),
        }
        self.transactions.append(new_transaction)
        self.save_data()
        return True
    
    def get_all_transactions(self):
        """獲取所有交易紀錄"""
        return self.transactions
        
    def delete_transaction(self, transaction_id):
        """刪除一筆交易"""
        original_count = len(self.transactions)
        self.transactions = [t for t in self.transactions if t['id'] != transaction_id]
        
        if len(self.transactions) < original_count:
            if self.save_data():
                print(f"🗑️ 已刪除交易 ID: {transaction_id}")
                return True
            else:
                print("❌ 刪除交易失敗，無法儲存資料")
                return False
        else:
            print("❌ 找不到要刪除的交易")
            return False

    def calculate_monthly_expenses(self, year_month):
        """
        根據給定的年月 (格式: "YYYY-MM") 彙總每月支出。
        """
        expense_totals = {}
        for transaction in self.transactions:
            if transaction.get('type') == 'expense' and transaction.get('date', '').startswith(year_month):
                category = transaction.get('budget_category')
                amount = transaction.get('amount')
                if category not in expense_totals:
                    expense_totals[category] = 0
                expense_totals[category] += amount
        return expense_totals

    def check_over_warnings(self, month=None):
        """檢查超支警告，回傳超支項目列表"""
        overspend_items = []
        months_to_check = [month] if month else self.budgets.keys()

        for check_month in months_to_check:
            if check_month in self.budgets:
                expense_totals = self.calculate_monthly_expenses(check_month)
                for category, spent_amount in expense_totals.items():
                    if category in self.budgets[check_month]:
                        budget_amount = self.budgets[check_month][category]["amount"]
                        if spent_amount > budget_amount:
                            overspend_items.append({
                                "month": check_month,
                                "category": category,
                                "budget": budget_amount,
                                "spent": spent_amount,
                                "overspend": spent_amount - budget_amount,
                            })
        return overspend_items