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

    def add_transaction(self, date_str, transaction_type, category, amount, description=""):
        """記錄一筆交易 (收入或支出)"""
        if amount <= 0:
            return False

        transaction = {
            "id": str(uuid.uuid4()),  # 使用 UUID 生成唯一ID
            "date": date_str,
            "type": transaction_type,
            "category": category,
            "amount": amount,
            "description": description,
            "timestamp": datetime.now().isoformat()
        }
        self.transactions.append(transaction)
        
        return self.save_data()
    
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

    def calculate_monthly_expenses(self, month):
        """計算某月各類別支出總額"""
        category_totals = {}
        for transaction in self.transactions:
            # 檢查交易是否屬於該月且為支出
            if transaction.get('type') == '支出' and transaction.get('date', '').startswith(month):
                category = transaction.get('category')
                amount = transaction.get('amount')
                if category not in category_totals:
                    category_totals[category] = 0
                category_totals[category] += amount
        return category_totals

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