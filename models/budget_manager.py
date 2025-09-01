import os
from datetime import datetime
from config import BUDGETS_FILE, EXPENSES_FILE
from utils import load_json_file, save_json_file

class BudgetManager:
    """
    管理預算與支出的核心邏輯。
    負責新增預算、記錄支出以及進行相關的純計算。
    """
    def __init__(self):
        self.budget_file = BUDGETS_FILE
        self.expense_file = EXPENSES_FILE
        self.budgets = {}
        self.expenses = {}
        self.load_data()

    def load_data(self):
        """載入 Budget/expense 資料"""
        self.budgets = load_json_file(self.budget_file, {})
        self.expenses = load_json_file(self.expense_file, {})
        if self.budgets:
            print(f"📖 載入現有預算: {len(self.budgets)} 個")
        else:
            print("🆕 建立新的預算")
        
        if self.expenses:
            print(f"📖 載入現有開銷: {len(self.expenses)} 個")
        else:
            print("🆕 建立新的開銷")

    def save_data(self):
        """儲存資料"""
        saved_budgets = save_json_file(self.budget_file, self.budgets)
        saved_expenses = save_json_file(self.expense_file, self.expenses)
        return saved_budgets and saved_expenses

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

    def add_expense(self, month, category, amount, description=""):
        """紀錄支出"""
        if amount <= 0:
            return False

        if month not in self.expenses:
            self.expenses[month] = {}

        if category not in self.expenses[month]:
            self.expenses[month][category] = []
        
        self.expenses[month][category].append({
            "date": datetime.now().isoformat(),
            "amount": amount,
            "description": description,
        })

        return self.save_data()
    
    def delete_expense(self, month, category, index):
        """刪除某月某類別的單筆支出"""
        if month in self.expenses and category in self.expenses[month]:
            try:
                #此處index 假設使用者從 1 開始輸入
                if 0 <= index -1 < len(self.expenses[month][category]):
                    deleted_expense = self.expenses[month][category].pop(index - 1)

                    if not self.expenses[month][category]:
                        del self.expenses[month][category]
                    if not self.expenses[month]:
                        del self.expenses[month]

                    if self.save_data():
                        print(f"🗑️ 已刪除 {month} {category} 的一筆支出: ${deleted_expense['amount']:,}")
                        return True
                    else:
                        print("❌ 刪除支出失敗，無法儲存資料")
                        return False
            except (ValueError, IndexError):
                print("❌ 無效的支出索引")
                return False
        
        print("❌ 找不到要刪除的支出")
        return False

    def calculate_monthly_expenses(self, month):
        """計算某月各類別支出總額"""
        if month not in self.expenses:
            return {}
        
        category_totals = {
            category: sum(expense["amount"] for expense in expense_list)
            for category, expense_list in self.expenses[month].items()
        }
        return category_totals

    def check_over_warnings(self, month=None):
        """檢查超支警告，回傳超支項目列表"""
        overspend_items = []
        months_to_check = [month] if month else self.expenses.keys()

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