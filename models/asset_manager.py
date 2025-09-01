import os
from datetime import datetime
from config import ASSETS_FILE, DEFAULT_CURRENCY
from utils import load_json_file, save_json_file, create_data_folder


class AssetManager:
    def __init__(self):
        self.data_file = ASSETS_FILE
        self.assets = {}
        create_data_folder()
        self.load_data()

    def load_data(self):
        """載入現有資料"""
        self.assets = load_json_file(self.data_file, {})
        if self.assets:
            print(f"📖 載入現有資料: {len(self.assets)} 個銀行帳戶")
        else:
            print("🆕 建立新的資產記錄")

    def save_data(self):
        """儲存資料"""
        return save_json_file(self.data_file, self.assets)

    def add_account(self, bank_name, account_type, balance):
        """新增銀行帳戶"""
        if bank_name not in self.assets:
            self.assets[bank_name] = {}

        self.assets[bank_name][account_type] = {
            "balance": balance,
            "last_update": datetime.now().isoformat(),
            "currency": DEFAULT_CURRENCY,
        }

        if self.save_data():
            print(f"✅ 已新增 {bank_name} {account_type}: ${balance:,}")
            return True
        else:
            print("❌ 新增帳戶失敗，無法儲存資料")
            return False

    def update_balance(self, bank_name, account_type, new_balance):
        """更新帳戶餘額"""
        if bank_name in self.assets and account_type in self.assets[bank_name]:
            old_balance = self.assets[bank_name][account_type]["balance"]
            change = new_balance - old_balance

            self.assets[bank_name][account_type]["balance"] = new_balance
            self.assets[bank_name][account_type]["last_update"] = datetime.now().isoformat()

            if self.save_data():
                print(f"🔄 {bank_name} {account_type}: ${old_balance:,} → ${new_balance:,} ({change:+,})")
                return True
            else:
                print("❌ 更新餘額失敗，無法儲存資料")
                return False
        else:
            print(f"❌ 找不到 {bank_name} 的 {account_type} 帳戶")
            return False

    def delete_account(self, bank_name, account_type):
        """刪除帳戶"""
        if bank_name in self.assets and account_type in self.assets[bank_name]:
            deleted_balance = self.assets[bank_name][account_type]["balance"]
            del self.assets[bank_name][account_type]

            if not self.assets[bank_name]:
                del self.assets[bank_name]

            if self.save_data():
                print(f"🗑️ 已刪除 {bank_name} {account_type} (原餘額: ${deleted_balance:,})")
                return True
            else:
                print("❌ 刪除帳戶失敗，無法儲存資料")
                return False
        else:
            print(f"❌ 找不到要刪除的帳戶")
            return False

    def calculate_totals(self):
        """計算各種總額"""
        result = {"總資產": 0, "活存": 0, "定存": 0, "投資": 0, "其他": 0}

        for bank_name, accounts in self.assets.items():
            for account_type, info in accounts.items():
                balance = info["balance"]
                result["總資產"] += balance

                if account_type in result:
                    result[account_type] += balance
                else:
                    result["其他"] += balance

        return result

    def show_all_accounts(self):
        """顯示所有帳戶"""
        if not self.assets:
            print("📭 目前沒有任何帳戶資料")
            return

        print("\n" + "=" * 50)
        print("💰 個人資產總覽")
        print("=" * 50)

        totals = self.calculate_totals()

        for bank_name, accounts in self.assets.items():
            print(f"\n🏦 {bank_name}")
            print("-" * 30)

            for account_type, info in accounts.items():
                balance = info["balance"]
                last_update = info["last_update"][:10]
                print(f"  💳 {account_type}: ${balance:,} (更新: {last_update})")

        print("\n" + "=" * 50)
        print("📊 總計")
        print("=" * 50)
        for category, amount in totals.items():
            if amount > 0:
                percentage = (amount / totals["總資產"] * 100) if totals["總資產"] > 0 else 0
                print(f"  {category}: ${amount:,} ({percentage:.1f}%)")
        print("=" * 50)