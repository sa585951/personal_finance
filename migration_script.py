import os
from datetime import datetime
from dotenv import load_dotenv
import uuid
import json
import sys

# 從共享模組匯入 engine 和資料表定義
from models.database import engine
from models.schema import metadata, assets_table, transactions_table, budget_months_table, budget_categories_table, goals_table

# 載入環境變數，主要用於讀取 JSON 檔案路徑
load_dotenv()

try:
    from config import ASSETS_FILE, TRANSACTIONS_FILE, BUDGETS_FILE, GOALS_FILE
    from utils import load_json_file
except ImportError as e:
    print(f"匯入 config 或 utils 時發生錯誤: {e}")
    print("請確保 config.py 和 utils.py 在專案頂層，且已正確匯入。")
    sys.exit(1)

# --- 遷移函數 (維持不變) ---

def migrate_assets():
    """遷移 assets.json 到 assets 資料表"""
    print("--- 開始遷移 assets.json ---")
    assets_data = load_json_file(ASSETS_FILE, {{}})
    
    if not isinstance(assets_data, dict):
        print("assets.json 格式錯誤，跳過遷移。")
        return

    rows_to_insert = []
    for account_key, data in assets_data.items():
        if isinstance(data, dict) and 'bank_name' in data and 'account_type' in data:
            try:
                balance = float(data.get('balance', 0))
                last_update_str = data.get('last_update')
                last_update_obj = datetime.fromisoformat(last_update_str) if last_update_str else None

                rows_to_insert.append({
                    'account_key': account_key,
                    'bank_name': data.get('bank_name'),
                    'account_type': data.get('account_type'),
                    'balance': balance,
                    'last_update': last_update_obj,
                    'currency': data.get('currency')
                })
            except (ValueError, TypeError) as e:
                print(f"警告: 帳戶 '{account_key}' 的資料轉換失敗: {e}，跳過。")
            except Exception as e:
                print(f"警告: 處理帳戶 '{account_key}' 時發生未知錯誤: {e}，跳過。")
        else:
            print(f"警告: 帳戶 '{account_key}' 資料格式錯誤，跳過。")
            
    if not rows_to_insert:
        print("沒有找到有效的 assets 資料可供遷移。")
        return

    try:
        with engine.connect() as connection:
            if rows_to_insert:
                connection.execute(assets_table.insert(), rows_to_insert)
                connection.commit()
                print(f"成功遷移 {len(rows_to_insert)} 筆 assets 資料。")
            else:
                print("未發現任何 assets 資料可遷移。")
    except Exception as e:
        print(f"遷移 assets 資料時發生錯誤: {e}")

def migrate_transactions():
    """遷移 transactions.json 到 transactions 資料表"""
    print("--- 開始遷移 transactions.json ---")
    transactions_data = load_json_file(TRANSACTIONS_FILE, [])
    
    if not isinstance(transactions_data, list):
        print("transactions.json 格式錯誤，跳過遷移。")
        return

    rows_to_insert = []
    for t in transactions_data:
        if isinstance(t, dict) and 'id' in t and 'date' in t and 'type' in t and 'amount' in t:
            try:
                amount = float(t.get('amount', 0))
                
                date_str = t.get('date')
                date_obj = None
                if date_str:
                    try:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError:
                        print(f"警告: 交易 ID '{t.get('id', 'N/A')}' 的日期格式 '{date_str}' 無效，跳過此紀錄。")
                        continue
                else:
                    print(f"警告: 交易 ID '{t.get('id', 'N/A')}' 缺少日期，跳過此紀錄。")
                    continue

                timestamp_str = t.get('timestamp')
                timestamp_obj = datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.now()

                rows_to_insert.append({
                    'id': uuid.UUID(t.get('id')),
                    'date': date_obj,
                    'type': t.get('type'),
                    'category': t.get('category', '未分類'),
                    'budget_category': t.get('budget_category'),
                    'amount': amount,
                    'description': t.get('description'),
                    'timestamp': timestamp_obj
                })
            except (ValueError, TypeError) as e:
                print(f"警告: 交易 ID '{t.get('id', 'N/A')}' 的資料轉換失敗: {e}，跳過。")
            except Exception as e:
                print(f"警告: 處理交易 ID '{t.get('id', 'N/A')}' 時發生未知錯誤: {e}，跳過。")
        else:
            print("警告: 交易資料格式錯誤，跳過。")

    if not rows_to_insert:
        print("沒有找到有效的 transactions 資料可供遷移。")
        return

    try:
        with engine.connect() as connection:
            if rows_to_insert:
                connection.execute(transactions_table.insert(), rows_to_insert)
                connection.commit()
                print(f"成功遷移 {len(rows_to_insert)} 筆 transactions 資料。")
            else:
                print("未發現任何 transactions 資料可遷移。")
    except Exception as e:
        print(f"遷移 transactions 資料時發生錯誤: {e}")

def migrate_budgets():
    """遷移 budgets.json 到 budget_months 和 budget_categories 資料表"""
    print("--- 開始遷移 budgets.json ---")
    budgets_data = load_json_file(BUDGETS_FILE, {{}})
    
    if not isinstance(budgets_data, dict):
        print("budgets.json 格式錯誤，跳過遷移。")
        return

    budget_months_rows = []
    budget_categories_rows = []

    for month, category_data in budgets_data.items():
        if isinstance(category_data, dict):
            month_created_date = datetime.now() 
            
            budget_months_rows.append({{'month': month, 'created_date': month_created_date}})

            for category_name, budget_details in category_data.items():
                if isinstance(budget_details, dict) and 'amount' in budget_details:
                    try:
                        amount = float(budget_details.get('amount', 0))
                        budget_created_date_str = budget_details.get("created_date")
                        budget_created_date_obj = datetime.fromisoformat(budget_created_date_str) if budget_created_date_str else month_created_date

                        budget_categories_rows.append({
                            'month': month,
                            'category_name': category_name,
                            'amount': amount,
                            'created_date': budget_created_date_obj,
                            'notes': budget_details.get('notes')
                        })
                    except (ValueError, TypeError) as e:
                        print(f"警告: 月份 '{month}', 類別 '{category_name}' 的資料轉換失敗: {e}，跳過。")
                    except Exception as e:
                        print(f"警告: 處理月份 '{month}', 類別 '{category_name}' 時發生未知錯誤: {e}，跳過。")
                else:
                    print(f"警告: 月份 '{month}', 類別 '{category_name}' 的預算細節格式錯誤，跳過。")
        else:
            print(f"警告: 月份 '{month}' 的預算資料格式錯誤，跳過。")

    if not budget_months_rows and not budget_categories_rows:
        print("沒有找到有效的 budgets 資料可供遷移。")
        return

    try:
        with engine.connect() as connection:
            if budget_months_rows:
                connection.execute(budget_months_table.insert(), budget_months_rows)
                print(f"成功遷移 {len(budget_months_rows)} 筆 budget_months 資料。")
            else:
                print("未發現任何 budget_months 資料可遷移。")
            
            if budget_categories_rows:
                connection.execute(budget_categories_table.insert(), budget_categories_rows)
                connection.commit()
                print(f"成功遷移 {len(budget_categories_rows)} 筆 budget_categories 資料。")
            else:
                print("未發現任何 budget_categories 資料可遷移。")
    except Exception as e:
        print(f"遷移 budgets 資料時發生錯誤: {e}")

def migrate_goals():
    """遷移 goals.json 到 goals 資料表"""
    print("--- 開始遷移 goals.json ---")
    goals_data = load_json_file(GOALS_FILE, {{}})
    
    if not isinstance(goals_data, dict):
        print("goals.json 格式錯誤，跳過遷移。")
        return

    rows_to_insert = []
    for goal_id, data in goals_data.items():
        if isinstance(data, dict) and 'title' in data:
            try:
                target_amount = float(data.get('target_amount', 0))
                current_amount = float(data.get('current_amount', 0))
                
                created_date_str = data.get("created_date")
                created_date_obj = datetime.fromisoformat(created_date_str) if created_date_str else datetime.now()
                
                last_update_str = data.get("last_update")
                last_update_obj = datetime.fromisoformat(last_update_str) if last_update_str else datetime.now()

                target_date_str = data.get("target_date")
                target_date_obj = None
                if target_date_str:
                    try:
                        target_date_obj = datetime.strptime(target_date_str, '%Y-%m-%d').date()
                    except ValueError:
                        print(f"警告: 目標 '{data.get('title', 'N/A')}' 的目標日期格式 '{target_date_str}' 無效，將不設定目標日期。")

                rows_to_insert.append({
                    'title': data.get('title'),
                    'type': data.get('type'),
                    'target_amount': target_amount,
                    'target_date': target_date_obj,
                    'current_amount': current_amount,
                    'created_date': created_date_obj,
                    'last_update': last_update_obj,
                    'status': data.get('status', 'active'),
                    'description': data.get('description')
                })
            except (ValueError, TypeError) as e:
                print(f"警告: 目標 ID '{goal_id}' 的資料轉換失敗: {e}，跳過。")
            except Exception as e:
                print(f"警告: 處理目標 ID '{goal_id}' 時發生未知錯誤: {e}，跳過。")
        else:
            print(f"警告: 目標 ID '{goal_id}' 資料格式錯誤，跳過。")
            
    if not rows_to_insert:
        print("沒有找到有效的 goals 資料可供遷移。")
        return

    try:
        with engine.connect() as connection:
            if rows_to_insert:
                connection.execute(goals_table.insert(), rows_to_insert)
                connection.commit()
                print(f"成功遷移 {len(rows_to_insert)} 筆 goals 資料。")
            else:
                print("未發現任何 goals 資料可遷移。")
    except Exception as e:
        print(f"遷移 goals 資料時發生錯誤: {e}")


# --- 主執行函數 ---
def main():
    """主執行函數，按順序執行所有遷移任務"""
    print("開始執行資料庫遷移腳本...")

    # 使用從 models.schema 匯入的 metadata
    metadata.create_all(engine)
    print("資料庫表格結構檢查/建立完成。")

    migrate_assets()
    migrate_transactions()
    migrate_budgets()
    migrate_goals()

    print("\n資料庫遷移腳本執行完畢！")

if __name__ == "__main__":
    main()
