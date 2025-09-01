import os
import json
from datetime import datetime
from asset_manager import AssetManager
from models.budget_manager import BudgetManager
from models.goal_manager import GoalManager
from reports.financial_reports import FinancialReports
from utils import create_data_folder

def main():
    """主程式進入點，提供使用者互動介面"""
    create_data_folder()
    
    # 建立核心物件
    asset_manager = AssetManager()
    budget_manager = BudgetManager()
    goal_manager = GoalManager()
    reports = FinancialReports(asset_manager, budget_manager, goal_manager)
    
    print("歡迎使用個人財務管理系統！")

    while True:
        print("\n" + "="*30)
        print("主選單")
        print("="*30)
        print("1. 查看財務報告")
        print("2. 管理資產")
        print("3. 管理預算與支出")
        print("4. 管理財務目標")
        print("0. 離開")

        choice = input("請選擇功能 (輸入編號): ")
        
        if choice == '1':
            show_reports_menu(reports)
        elif choice == '2':
            manage_assets_menu(asset_manager)
        elif choice == '3':
            manage_budgets_menu(budget_manager)
        elif choice == '4':
            manage_goals_menu(goal_manager)
        elif choice == '0':
            print("感謝使用，再見！")
            break
        else:
            print("❌ 無效的選擇，請重新輸入。")

def show_reports_menu(reports):
    """查看報告選單"""
    while True:
        print("\n--- 財務報告 ---")
        print("1. 顯示所有帳戶")
        print("2. 顯示當月消費總覽")
        print("3. 顯示超支警告")
        print("4. 顯示所有財務目標")
        print("0. 返回主選單")
        
        choice = input("請選擇報告項目: ")
        
        if choice == '1':
            reports.show_all_accounts()
        elif choice == '2':
            month = input("請輸入月份 (YYYY-MM): ")
            reports.show_monthly_summary(month)
        elif choice == '3':
            reports.show_overspend_warnings()
        elif choice == '4':
            reports.show_all_goals()
        elif choice == '0':
            break
        else:
            print("❌ 無效的選擇。")

def manage_assets_menu(manager):
    """管理資產選單"""
    while True:
        print("\n--- 管理資產 ---")
        print("1. 新增帳戶")
        print("2. 更新帳戶餘額")
        print("3. 刪除帳戶")
        print("0. 返回主選單")
        
        choice = input("請選擇操作: ")
        if choice == '1':
            bank = input("請輸入銀行名稱: ")
            account = input("請輸入帳戶類型 (活存, 定存, 投資等): ")
            balance = float(input("請輸入初始餘額: "))
            manager.add_account(bank, account, balance)
        elif choice == '2':
            bank = input("請輸入銀行名稱: ")
            account = input("請輸入帳戶類型: ")
            new_balance = float(input("請輸入新的餘額: "))
            manager.update_balance(bank, account, new_balance)
        elif choice == '3':
            bank = input("請輸入銀行名稱: ")
            account = input("請輸入帳戶類型: ")
            manager.delete_account(bank, account)
        elif choice == '0':
            break
        else:
            print("❌ 無效的選擇。")

def manage_budgets_menu(manager):
    """管理預算與支出選單"""
    while True:
        print("\n--- 管理預算與支出 ---")
        print("1. 設定預算")
        print("2. 記錄支出")
        print("3. 刪除預算")
        print("4. 刪除支出")
        print("0. 返回主選單")
        
        choice = input("請選擇操作: ")
        if choice == '1':
            month = input("請輸入月份 (YYYY-MM): ")
            category = input("請輸入類別: ")
            amount = float(input("請輸入預算金額: "))
            manager.set_budget(month, category, amount)
        elif choice == '2':
            month = input("請輸入月份 (YYYY-MM): ")
            category = input("請輸入類別: ")
            amount = float(input("請輸入支出金額: "))
            description = input("請輸入說明: ")
            manager.add_expense(month, category, amount, description)
        elif choice == '3':
            month = input("請輸入月份 (YYYY-MM): ")
            category = input("請輸入類別: ")
            manager.delete_budget(month, category)
        elif choice == '4':
            month = input("請輸入月份 (YYYY-MM): ")
            category = input("請輸入類別: ")
            index = int(input("請輸入要刪除的支出編號 (從1開始): "))
            manager.delete_expense(month, category, index)
        elif choice == '0':
            break
        else:
            print("❌ 無效的選擇。")

def manage_goals_menu(manager):
    """管理財務目標選單"""
    while True:
        print("\n--- 管理財務目標 ---")
        print("1. 新增目標")
        print("2. 更新目標進度")
        print("3. 刪除目標")
        print("0. 返回主選單")
        
        choice = input("請選擇操作: ")
        if choice == '1':
            title = input("請輸入目標名稱: ")
            goal_type = input("請輸入目標類型 (e.g., 旅遊, 買房): ")
            target_amount = float(input("請輸入目標金額: "))
            target_date = input("請輸入目標日期 (YYYY-MM-DD): ")
            description = input("請輸入說明: ")
            manager.add_goal(title, goal_type, target_amount, target_date, description)
        elif choice == '2':
            goal_id = input("請輸入目標ID: ")
            new_amount = float(input("請輸入目前金額: "))
            manager.update_goal_progress(goal_id, new_amount)
        elif choice == '3':
            goal_id = input("請輸入目標ID: ")
            manager.delete_goal(goal_id)
        elif choice == '0':
            break
        else:
            print("❌ 無效的選擇。")

if __name__ == "__main__":
    main()