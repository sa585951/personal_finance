class FinancialReports:
    """
    負責生成各種財務報告。
    此類別不負責修改資料，僅從 Manager 類別中讀取資料並格式化輸出。
    """
    def __init__(self, asset_manager, budget_manager, goal_manager):
        self.asset_manager = asset_manager
        self.budget_manager = budget_manager
        self.goal_manager = goal_manager

    def show_all_accounts(self):
        """顯示所有資產帳戶的總覽"""
        assets = self.asset_manager.assets
        if not assets:
            print("📭 目前沒有任何帳戶資料")
            return

        print("\n" + "=" * 50)
        print("💰 個人資產總覽")
        print("=" * 50)

        totals = self.asset_manager.calculate_totals()

        for bank_name, accounts in assets.items():
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

    def show_monthly_summary(self, month):
        """顯示某月消費總覽"""
        expense_totals = self.budget_manager.calculate_monthly_expenses(month)
        
        if not expense_totals:
            print(f"📭 {month} 無支出記錄")
            return
        
        budgets = self.budget_manager.budgets.get(month, {})
        total_expenses = sum(expense_totals.values())
        
        print(f"\n=== {month} 消費總覽 ===")
        print(f"總消費: ${total_expenses:,}")
        print()
        
        for category, amount in expense_totals.items():
            percentage = (amount / total_expenses * 100) if total_expenses > 0 else 0
            
            if category in budgets:
                budget_amount = budgets[category]["amount"]
                remaining = budget_amount - amount
                
                if remaining >= 0:
                    print(f"{category}: ${amount:,} ({percentage:.1f}%) [預算: ${budget_amount:,}] 剩餘: ${remaining:,}")
                else:
                    print(f"{category}: ${amount:,} ({percentage:.1f}%) [預算: ${budget_amount:,}] 超支: ${-remaining:,} ⚠️")
            else:
                print(f"{category}: ${amount:,} ({percentage:.1f}%) [無預算設定]")

    def show_overspend_warnings(self, month=None):
        """顯示超支警告報告"""
        overspend_items = self.budget_manager.check_over_warnings(month)

        if not overspend_items:
            if month:
                print(f"✔ {month} 無超支情況")
            else:
                print("✔ 目前無超支情況")
            return
        
        print("\n⚠️ 超支警告報告")
        print("=" * 30)

        current_month = ""
        total_overspend = 0

        for item in overspend_items:
            if item["month"] != current_month:
                if current_month:
                    print()
                current_month = item["month"]
                print(f"\n📅 {current_month}:")

            print(f"  🚨 {item['category']}: 超支 ${item['overspend']:,} "
            f"(預算: ${item['budget']:,}, 實際: ${item['spent']:,})")
            
            total_overspend += item["overspend"]

        print("\n" + "=" * 30)
        print(f"💸 總超支金額: ${total_overspend:,}")

        if len(overspend_items) >= 3:
            print("\n💡 建議檢視預算設定是否合理，或加強支出控制")
        elif total_overspend > 10000:
            print("\n💡 超支金額較大，建議調整消費習慣")
            
    def show_all_goals(self):
        """顯示所有財務目標"""
        goals = self.goal_manager.get_all_goals()
        if not goals:
            print("📭 目前沒有任何目標")
            return
        
        print("\n" + "=" * 50)
        print("🎯 財務目標總覽")
        print("=" * 50)
        
        for goal_id, goal in goals.items():
            progress_percent = (goal['current_amount'] / goal['target_amount'] * 100) if goal['target_amount'] > 0 else 0
            
            print(f"\n▪️ **{goal['title']}** (ID: {goal_id})")
            print(f"  目標: ${goal['target_amount']:,}")
            print(f"  進度: ${goal['current_amount']:,} ({progress_percent:.1f}%)")
            print(f"  類型: {goal['type']}")
            print(f"  狀態: {goal['status']}")
            print(f"  備註: {goal['description'] if goal['description'] else '無'}")
            
            if goal['status'] == 'active':
                remaining_amount = goal['target_amount'] - goal['current_amount']
                print(f"  尚需: ${remaining_amount:,}")
            
        print("\n" + "=" * 50)