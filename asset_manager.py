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
            print(f"❌載入資料失敗: {e}")
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

    def get_bank_total(self, bank_name):
        """計算某家銀行的總資產"""
        if bank_name in self.assets:
            total = 0
            bank_data = self.assets[bank_name]
            for account_type in bank_data:
                total += bank_data[account_type]["balance"]

            return total
        else:
            print (f"目前沒有{bank_name}帳戶的任何資料")
            return 0
        
    def get_richest_bank(self):
        """找出資產最多的銀行"""
        if not self.assets:
            print("目前沒有任何銀行資料")
            return None
    
        richest_bank = ""
        max_amount = 0

        for bank_name in self.assets:
            current_total = self.get_bank_total(bank_name)

            if current_total > max_amount:
                max_amount = current_total
                richest_bank = bank_name

        return richest_bank, max_amount
    
    def analyze_asset_distribution(self):
        """分析資產分佈"""
        totals = self.calculate_totals()
        total_assets = totals["總資產"]

        if total_assets == 0:
            print("目前沒有資產資料")
            return

        活存百分比 = (totals["活存"] / totals["總資產"]) * 100
        定存百分比 = (totals["定存"] / totals["總資產"]) * 100
        投資百分比 = (totals["投資"] / totals["總資產"]) * 100

        print(f"\n📊 資產分佈分析")
        print(f"活存: ${totals['活存']:,} ({活存百分比:.1f}%)")
        print(f"定存: ${totals['定存']:,} ({定存百分比:.1f}%)")
        print(f"投資: ${totals['投資']:,} ({投資百分比:.1f}%)")

        print(f"\n💡 理財建議:")
    
        if 活存百分比 > 60:
            print("⚠️  活存比例過高，建議增加投資以對抗通膨")
        elif 活存百分比 < 10:
            print("⚠️  活存比例過低，建議保留緊急預備金")
        else:
            print("✅ 活存比例適中")

        if 投資百分比 < 20:
            print("💡 投資比例較低，可考慮增加以提升報酬率")
        elif 投資百分比 > 70:
            print("⚠️  投資比例較高，注意風險控制")

        if 定存百分比 > 50:
            print("💡 定存比例較高，報酬率可能不足以對抗通膨")

    def calculate_financial_health_score(self):
        """計算財務健康評分"""
        totals = self.calculate_totals()

        if totals["總資產"] == 0 :
            print("目前查無資產")
            return 0
        
        活存比例 = (totals["活存"] / totals["總資產"])
        投資比例 = (totals["投資"] / totals["總資產"])
        total_banks = len(self.assets)
        score = 0

        if (活存比例 >= 0.1 ) and (活存比例 <= 0.4):
            score = score + 30
        elif (活存比例 <0.1 and 活存比例 >= 0.05) or (活存比例 > 0.4 and 活存比例 <=0.5):
            score = score + 20
        else :
            score = score + 10
        
        if(投資比例 >= 0.2) and (投資比例 <=0.6):
            score = score + 30
        elif (投資比例 <0.2 and 投資比例 >= 0.05) or (投資比例 > 0.6 and 投資比例 <=0.8):
            score = score + 20
        else :
            score = score + 10

        if total_banks >= 2:
            score = score + 40
        elif total_banks == 1:
            score = score + 10

        return score

    def calculate_risk_assessment(self):
        """計算風險評估 - 純計算，回傳結果"""
        totals = self.calculate_totals()

        if totals["總資產"] == 0:
            return{"流動性": "無資料", "時間": " 無資料"}
        
        快速可用資產 = totals["活存"]
        流動性比例 = 快速可用資產 / totals["總資產"]

        if 流動性比例 >= 0.6:
            流動性風險 = "低"
        elif 流動性比例 >= 0.3:
            流動性風險 = "中"
        else:
            流動性風險 = "高"

        最舊時間 = datetime.now().isoformat()

        for bank_name, accounts in self.assets.items():
            for account_type, info in accounts.items():
                if info["last_update"] < 最舊時間:
                    最舊時間 = info["last_update"]

        最舊日期 = datetime.fromisoformat(最舊時間)
        現在日期 = datetime.now()

        差距天數 = (現在日期 - 最舊日期).days

        if 差距天數 <= 7:
            時間風險 = "低"
        elif 差距天數 <=30:
            時間風險 = "中"
        else:
            時間風險 = "高"

        return {"流動性": 流動性風險, "時間": 時間風險}
    
    def find_oldest_account(self):
        """找出最久沒更新的帳戶"""
        最舊時間 = datetime.now().isoformat()
        最舊銀行 = ""
        最舊帳戶 = ""
    
        for bank_name, accounts in self.assets.items():
            for account_type, info in accounts.items():
                if info["last_update"] < 最舊時間:
                    最舊時間 = info["last_update"]
                    最舊銀行 = bank_name
                    最舊帳戶 = account_type
                
        return 最舊銀行, 最舊帳戶, 最舊時間

class BudgetManager:
    def __init__(self):
        self.budget_file = "data/budgets.json"
        self.expense_file = "data/expenses.json"

        #初始化資料結構
        self.budgets = {}
        self.expenses= {}

        self.load_data()


    def load_data(self):
        """載入Budget/expense資料"""
        try:
            if os.path.exists(self.budget_file):
                with open(self.budget_file, "r", encoding="utf-8") as b:
                    self.budgets = json.load(b)
                print(f"📖 載入現有資料: {len(self.budgets)} 預算")
            else:
                self.budgets ={}
                print("🆕 建立新的預算")
        
            if os.path.exists(self.expense_file):
                with open(self.expense_file, "r", encoding="utf-8") as e:
                    self.expenses = json.load(e)
                print(f"📖 載入現有資料: {len(self.expenses)} 開銷")
            else:
                self.expenses = {}
                print("🆕 建立新的開銷")
        except Exception as e:
            print(f"❌載入資料失敗: {e}")
            self.budgets ={}
            self.expenses = {}
    
    def save_data(self):
        try:
            with open(self.budget_file, "w", encoding="utf-8") as b:
                json.dump(self.budgets, b, indent=2, ensure_ascii=False)
            with open(self.expense_file, "w", encoding="utf-8") as e:
                json.dump(self.expenses, e, indent=2, ensure_ascii=False)
            print("💾 資料已儲存")
        except Exception as e:
            print(f"❌ 儲存失敗: {e}")

    def set_budget(self, month, category, amount):
        """設定某月某類別的預算"""
        if month not in self.budgets:
            self.budgets[month] = {}

        self.budgets[month][category] = {
            "amounts" = amount
        }

class MenuManager:
    """選單管理類別 - 負責所有選單相關的功能"""
    
    def __init__(self, asset_manager):
        self.asset_manager = asset_manager
    
    def show_main_menu(self):
        """顯示主選單"""
        print("\n" + "="*50)
        print("🏦 個人資產管理系統")
        print("="*50)
        print("1. 📊 基本功能 - 帳戶管理")
        print("2. 📈 分析功能 - 資產分析")
        print("3. 🛠️  工具功能 - 實用工具")
        print("4. 👋 離開系統")
        print("="*50)
    
    def show_basic_menu(self):
        """顯示基本功能選單"""
        print("\n" + "-"*40)
        print("📊 基本功能選單")
        print("-"*40)
        print("1. 顯示所有帳戶")
        print("2. 新增帳戶")
        print("3. 更新餘額")
        print("4. 刪除帳戶")
        print("0. 返回主選單")
        print("-"*40)
    
    def show_analysis_menu(self):
        """顯示分析功能選單"""
        print("\n" + "-"*40)
        print("📈 分析功能選單")
        print("-"*40)
        print("1. 資產分佈分析")
        print("2. 查詢銀行總資產")
        print("3. 尋找最富有的銀行")
        print("4. 財務健康評分")
        print("5. 風險評估")
        print("0. 返回主選單")
        print("-"*40)
    
    def show_tools_menu(self):
        """顯示工具功能選單"""
        print("\n" + "-"*40)
        print("🛠️ 工具功能選單")
        print("-"*40)
        print("1. 匯出資料到CSV")
        print("2. 從CSV匯入資料 (即將推出)")
        print("3. 備份資料")
        print("4. 還原資料 (即將推出)")
        print("0. 返回主選單")
        print("-"*40)
    
    def handle_basic_functions(self):
        """處理基本功能"""
        while True:
            self.show_basic_menu()
            choice = input("請選擇功能 (0-4): ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                self.asset_manager.show_all_accounts()
            elif choice == "2":
                self._add_account()
            elif choice == "3":
                self._update_balance()
            elif choice == "4":
                self._delete_account()
            else:
                print("❌ 無效選擇，請重新輸入")
            
            input("\n按 Enter 鍵繼續...")
    
    def handle_analysis_functions(self):
        """處理分析功能"""
        while True:
            self.show_analysis_menu()
            choice = input("請選擇功能 (0-5): ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                self.asset_manager.analyze_asset_distribution()
            elif choice == "2":
                self._query_bank_total()
            elif choice == "3":
                self._find_richest_bank()
            elif choice == "4":
                self._show_health_analysis()
            elif choice == "5":
                self._show_risk_analysis()
            else:
                print("❌ 無效選擇，請重新輸入")
            
            input("\n按 Enter 鍵繼續...")
    
    def handle_tools_functions(self):
        """處理工具功能"""
        while True:
            self.show_tools_menu()
            choice = input("請選擇功能 (0-4): ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                print("🚧 CSV匯出功能正在開發中...")
            elif choice == "2":
                print("🚧 CSV匯入功能正在開發中...")
            elif choice == "3":
                print("🚧 備份功能正在開發中...")
            elif choice == "4":
                print("🚧 還原功能正在開發中...")
            else:
                print("❌ 無效選擇，請重新輸入")
            
            input("\n按 Enter 鍵繼續...")
    
    # 私有方法 - 處理具體的輸入輸出
    def _add_account(self):
        """新增帳戶的輸入處理"""
        print("\n➕ 新增帳戶")
        bank_name = input("銀行名稱: ").strip()
        account_type = input("帳戶類型 (活存/定存/投資): ").strip()
        try:
            balance = int(input("餘額: ").strip())
            self.asset_manager.add_account(bank_name, account_type, balance)
        except ValueError:
            print("❌ 請輸入有效的數字")
    
    def _update_balance(self):
        """更新餘額的輸入處理"""
        print("\n🔄 更新餘額")
        bank_name = input("銀行名稱: ").strip()
        account_type = input("帳戶類型: ").strip()
        try:
            new_balance = int(input("新餘額: ").strip())
            self.asset_manager.update_balance(bank_name, account_type, new_balance)
        except ValueError:
            print("❌ 請輸入有效的數字")
    
    def _delete_account(self):
        """刪除帳戶的輸入處理"""
        print("\n🗑️ 刪除帳戶")
        bank_name = input("銀行名稱: ").strip()
        account_type = input("帳戶類型: ").strip()
        confirm = input(f"確定要刪除 {bank_name} 的 {account_type} 嗎? (y/n): ").strip().lower()
        if confirm == 'y':
            self.asset_manager.delete_account(bank_name, account_type)
    
    def _query_bank_total(self):
        """查詢銀行總資產的輸入處理"""
        print("\n🏦 查詢銀行總資產")
        bank_name = input("銀行名稱: ").strip()
        total = self.asset_manager.get_bank_total(bank_name)
        if total > 0:
            print(f"💰 {bank_name} 總資產: ${total:,}")
    
    def _find_richest_bank(self):
        """尋找最富有銀行的處理"""
        print("\n👑 尋找最富有的銀行")
        result = self.asset_manager.get_richest_bank()
        if result:
            bank_name, amount = result
            print(f"🏆 最富有的銀行: {bank_name}")
            print(f"💰 總資產: ${amount:,}")

    def _show_health_analysis(self):
        """顯示健康分析和建議"""
        score = self.asset_manager.calculate_financial_health_score()
        print(f"🏥 財務健康評分: {score}/100 分")

        if score > 80:
            print("💪 財務狀況優良！")
        elif score >= 60:
            print("👍 財務狀況良好，還有改善空間")
        else:
            print("建議改善資產分配狀況!")

    def _show_risk_analysis(self):
        """顯示風險分析"""
        result = self.asset_manager.calculate_risk_assessment()

        print("\n🎯 風險評估報告")
        print("="*30)
        print(f"💧 流動性風險: {result['流動性']}")
        print(f"⏰ 時間風險: {result['時間']}")
    
    
        if result['流動性'] == "高":
            print("⚠️ 建議增加活存比例以應付緊急狀況")
    
        if result['時間'] == "高":
            print("⚠️ 建議盡快更新資產資料")
        
        if result['時間'] != "低":
            最舊銀行, 最舊帳戶, 最舊時間 = self.asset_manager.find_oldest_account()
            print(f"📅 最久未更新: {最舊銀行} {最舊帳戶} ({最舊時間[:10]})")

def main():
    """主程式入口"""
    # 建立物件
    asset_manager = AssetManager()
    menu_manager = MenuManager(asset_manager)
    budget_manager = BudgetManager()
    
    # 主選單循環
    while True:
        menu_manager.show_main_menu()
        choice = input("請選擇功能 (1-4): ").strip()
        
        if choice == "1":
            menu_manager.handle_basic_functions()
        elif choice == "2":
            menu_manager.handle_analysis_functions()
        elif choice == "3":
            menu_manager.handle_tools_functions()
        elif choice == "4":
            print("👋 感謝使用個人資產管理系統！再見！")
            break
        else:
            print("❌ 無效選擇，請重新輸入")


if __name__ == "__main__":
    main()