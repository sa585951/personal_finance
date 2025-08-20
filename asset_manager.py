import json
import os
from datetime import datetime

class AssetManager:
    def __init__(self):
        self.data_file = "data/assets.json"
        self.assets = {}
        self.create_data_folder()
        self.load_data()
    
    def create_data_folder(self):
        """建立資料夾"""
        if not os.path.exists("data"):
            os.makedirs("data")
            print("📁 建立 data 資料夾")
    
    def load_data(self):
        """載入現有資料"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r", encoding="utf-8") as f:
                    self.assets = json.load(f)
                print(f"📖 載入現有資料: {len(self.assets)} 個銀行帳戶")
            else:
                self.assets = {}
                print("🆕 建立新的資產記錄")
        except Exception as e:
            print(f"❌ 載入資料失敗: {e}")
            self.assets = {}
    
    def save_data(self):
        """儲存資料"""
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.assets, f, indent=2, ensure_ascii=False)
            print("💾 資料已儲存")
        except Exception as e:
            print(f"❌ 儲存失敗: {e}")
    
    def add_account(self, bank_name, account_type, balance):
        """新增銀行帳戶"""
        if bank_name not in self.assets:
            self.assets[bank_name] = {}
        
        self.assets[bank_name][account_type] = {
            "balance": balance,
            "last_update": datetime.now().isoformat(),
            "currency": "TWD"
        }
        
        self.save_data()
        print(f"✅ 已新增 {bank_name} {account_type}: ${balance:,}")
    
    def update_balance(self, bank_name, account_type, new_balance):
        """更新帳戶餘額"""
        if bank_name in self.assets and account_type in self.assets[bank_name]:
            old_balance = self.assets[bank_name][account_type]["balance"]
            change = new_balance - old_balance
            
            self.assets[bank_name][account_type]["balance"] = new_balance
            self.assets[bank_name][account_type]["last_update"] = datetime.now().isoformat()
            
            self.save_data()
            print(f"🔄 {bank_name} {account_type}: ${old_balance:,} → ${new_balance:,} ({change:+,})")
        else:
            print(f"❌ 找不到 {bank_name} 的 {account_type} 帳戶")
    
    def delete_account(self, bank_name, account_type):
        """刪除帳戶"""
        if bank_name in self.assets and account_type in self.assets[bank_name]:
            deleted_balance = self.assets[bank_name][account_type]["balance"]
            del self.assets[bank_name][account_type]
            
            # 如果銀行沒有其他帳戶，刪除整個銀行
            if not self.assets[bank_name]:
                del self.assets[bank_name]
            
            self.save_data()
            print(f"🗑️ 已刪除 {bank_name} {account_type} (原餘額: ${deleted_balance:,})")
        else:
            print(f"❌ 找不到要刪除的帳戶")
    
    def calculate_totals(self):
        """計算各種總額"""
        result = {
            "總資產": 0,
            "活存": 0,
            "定存": 0,
            "投資": 0,
            "其他": 0
        }
        
        for bank_name, accounts in self.assets.items():
            for account_type, info in accounts.items():
                balance = info["balance"]
                result["總資產"] += balance
                
                # 分類計算
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
        
        print("\n" + "="*50)
        print("💰 個人資產總覽")
        print("="*50)
        
        totals = self.calculate_totals()
        
        for bank_name, accounts in self.assets.items():
            print(f"\n🏦 {bank_name}")
            print("-" * 30)
            
            for account_type, info in accounts.items():
                balance = info["balance"]
                last_update = info["last_update"][:10]  # 只顯示日期
                print(f"  💳 {account_type}: ${balance:,} (更新: {last_update})")
        
        print("\n" + "="*50)
        print("📊 總計")
        print("="*50)
        for category, amount in totals.items():
            if amount > 0:
                percentage = (amount / totals["總資產"] * 100) if totals["總資產"] > 0 else 0
                print(f"  {category}: ${amount:,} ({percentage:.1f}%)")
        print("="*50)

# 測試用的簡單命令行介面
def main():
    """簡單的命令行介面"""
    asset_manager = AssetManager()
    
    while True:
        print("\n🏦 個人資產管理系統")
        print("1. 顯示所有帳戶")
        print("2. 新增帳戶")
        print("3. 更新餘額")
        print("4. 刪除帳戶")
        print("5. 離開")
        
        choice = input("\n請選擇功能 (1-5): ").strip()
        
        if choice == "1":
            asset_manager.show_all_accounts()
        
        elif choice == "2":
            print("\n➕ 新增帳戶")
            bank_name = input("銀行名稱: ").strip()
            account_type = input("帳戶類型 (活存/定存/投資): ").strip()
            try:
                balance = int(input("餘額: ").strip())
                asset_manager.add_account(bank_name, account_type, balance)
            except ValueError:
                print("❌ 請輸入有效的數字")
        
        elif choice == "3":
            print("\n🔄 更新餘額")
            bank_name = input("銀行名稱: ").strip()
            account_type = input("帳戶類型: ").strip()
            try:
                new_balance = int(input("新餘額: ").strip())
                asset_manager.update_balance(bank_name, account_type, new_balance)
            except ValueError:
                print("❌ 請輸入有效的數字")
        
        elif choice == "4":
            print("\n🗑️ 刪除帳戶")
            bank_name = input("銀行名稱: ").strip()
            account_type = input("帳戶類型: ").strip()
            confirm = input(f"確定要刪除 {bank_name} 的 {account_type} 嗎? (y/n): ").strip().lower()
            if confirm == 'y':
                asset_manager.delete_account(bank_name, account_type)
        
        elif choice == "5":
            print("👋 再見！")
            break
        
        else:
            print("❌ 無效選擇，請重新輸入")

if __name__ == "__main__":
    main()