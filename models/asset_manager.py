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

    def _get_account_key(self, bank_name, account_type):
        """生成唯一的帳戶 ID，用於內部存取"""
        return f"{bank_name}-{account_type}"
        
    def load_data(self):
        """載入現有資料，並處理舊格式與不合法資料"""
        raw_data = load_json_file(self.data_file, {})
        
        # 檢查最外層資料結構是否為字典
        if not isinstance(raw_data, dict):
            print("⚠️ 警告: assets.json 檔案格式錯誤，已重設為空資料。")
            self.assets = {}
            return
                
        self.assets = raw_data

        valid_assets = {}
        for account_id, data in self.assets.items():
            if isinstance(data, dict) and 'bank_name' in data and 'account_type' in data:
                valid_assets[account_id] = data
            else:
                print(f"⚠️ 警告: '{account_id}' 的資料格式錯誤，已跳過。")
                
        self.assets = valid_assets
        
        if self.assets:
            print(f"載入現有資產資料: {len(self.assets)} 個帳戶")
        else:
            print("🆕 建立新的資產記錄")

    def save_data(self):
        """儲存資料"""
        # 將資料以扁平格式儲存
        return save_json_file(self.data_file, self.assets)

    def get_all_assets(self):
        """
        獲取所有資產，並以唯一的 ID 作為 key。
        這個方法直接回傳 self.assets，方便前端使用。
        """
        return self.assets

    def add_account(self, bank_name, account_type, balance):
        """新增銀行帳戶"""
        account_key = self._get_account_key(bank_name, account_type)
        
        if account_key in self.assets:
            print("❌ 帳戶已存在")
            return False, "該帳戶已存在"
            
        self.assets[account_key] = {
            "bank_name": bank_name,
            "account_type": account_type,
            "balance": balance,
            "last_update": datetime.now().isoformat(),
            "currency": DEFAULT_CURRENCY,
        }
        
        if self.save_data():
            print(f"✅ 已新增 {bank_name} {account_type}: ${balance:,}")
            return True, "成功新增帳戶"
        else:
            return False, "新增帳戶失敗"

    def update_balance(self, account_id, new_balance):
        """更新指定 ID 帳戶的餘額"""
        if account_id not in self.assets:
            print("❌ 找不到此帳戶")
            return False, "找不到此帳戶"
        if new_balance < 0:
            print("❌ 餘額不能為負數")
            return False, "餘額不能為負數"
        
        old_balance = self.assets[account_id]["balance"]
        change = new_balance - old_balance

        self.assets[account_id]["balance"] = new_balance
        self.assets[account_id]["last_update"] = datetime.now().isoformat()
        
        if self.save_data():
            print(f"🔄 {account_id}: ${old_balance:,} → ${new_balance:,} ({change:+,})")
            return True, "餘額更新成功"
        else:
            return False, "餘額更新失敗"

    def delete_account(self, account_id):
        """刪除帳戶"""
        if account_id in self.assets:
            deleted_balance = self.assets[account_id]["balance"]
            del self.assets[account_id]

            if self.save_data():
                print(f"🗑️ 已刪除帳戶 {account_id} (原餘額: ${deleted_balance:,})")
                return True, "成功刪除帳戶"
            else:
                return False, "刪除帳戶失敗，無法儲存資料"
        else:
            print("❌ 找不到要刪除的帳戶")
            return False, "找不到要刪除的帳戶"

    def transfer(self, source_id, dest_id, amount):
        """處理帳戶間轉帳"""
        if source_id not in self.assets or dest_id not in self.assets:
            print("❌ 來源或目標帳戶不存在")
            return False, "來源或目標帳戶不存在"
        if amount <= 0:
            print("❌ 轉帳金額必須大於0")
            return False, "轉帳金額必須大於0"
        
        source_account = self.assets[source_id]
        dest_account = self.assets[dest_id]

        if source_account['balance'] < amount:
            print("❌ 來源帳戶餘額不足")
            return False, "來源帳戶餘額不足"
            
        try:
            source_account['balance'] -= amount
            dest_account['balance'] += amount
            
            if self.save_data():
                print(f"✅ 成功從 {source_account['bank_name']} ({source_account['account_type']}) 轉帳 ${amount:,} 至 {dest_account['bank_name']} ({dest_account['account_type']})")
                return True, "轉帳成功"
            else:
                source_account['balance'] += amount
                dest_account['balance'] -= amount
                print("❌ 轉帳失敗，無法儲存資料")
                return False, "轉帳失敗，無法儲存資料"
        except Exception as e:
            print(f"❌ 轉帳過程中發生錯誤: {e}")
            return False, "轉帳過程中發生錯誤"
            
    def calculate_totals(self):
        """計算各種總額"""
        result = {"總資產": 0, "活存": 0, "定存": 0, "投資": 0, "其他": 0}
        
        for account_id, info in self.assets.items():
            balance = info.get("balance", 0)
            account_type = info.get("account_type", "其他")
            
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

        # 這裡需要調整顯示邏輯，因為 assets 不再是巢狀字典
        for account_id, info in self.assets.items():
            bank_name = info['bank_name']
            account_type = info['account_type']
            balance = info['balance']
            last_update = info['last_update'][:10]
            print(f"🏦 {bank_name} - 💳 {account_type}: ${balance:,} (更新: {last_update})")

        print("\n" + "=" * 50)
        print("📊 總計")
        print("=" * 50)
        for category, amount in totals.items():
            if amount > 0:
                percentage = (amount / totals["總資產"] * 100) if totals["總資產"] > 0 else 0
                print(f"  {category}: ${amount:,} ({percentage:.1f}%)")
        print("=" * 50)