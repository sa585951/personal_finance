from datetime import datetime
import sys
sys.stdout.reconfigure(encoding='utf-8')
from flask import Flask, jsonify, request
from flask_cors import CORS

# 為了確保匯入正確，我們需要將專案根目錄加入到路徑
# 這樣 Flask 才能找到我們的 models 和 reports

# 匯入我們之前建立的核心類別
from models.asset_manager import AssetManager
from models.budget_manager import BudgetManager
from models.goal_manager import GoalManager

# 實例化 Flask 應用程式
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https:personal-finance-gilt.vercel.app"}})

# 實例化 Manager 類別，它們將在整個應用程式中被重複使用
asset_manager = AssetManager()
budget_manager = BudgetManager()
goal_manager = GoalManager()

@app.route("/")
def home():
    """根路由，回傳歡迎訊息"""
    return "歡迎來到個人財務管理系統的後端 API！"

# API - 資產管理

@app.route("/api/assets", methods=["GET"])
def get_assets():
    assets = asset_manager.get_all_assets()
    return jsonify({"success": True, "data": assets}), 200

@app.route("/api/assets", methods=["POST"])
def add_asset():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "缺少資料"}), 400
    
    bank_name = data.get("bank_name")
    account_type = data.get("account_type")
    initial_balance = data.get("initial_balance")

    if not all([bank_name, account_type, initial_balance is not None]):
        return jsonify({"success": False, "message": "缺少必要欄位"}), 400

    success, message = asset_manager.add_account(bank_name, account_type, initial_balance)
    if success:
        return jsonify({"success": True, "message": message}), 201
    else:
        return jsonify({"success": False, "message": message}), 409 # Conflict

@app.route("/api/assets/<account_id>", methods=["PUT"])
def update_asset_balance(account_id):
    data = request.get_json()
    new_balance = data.get('new_balance')
    if new_balance is None:
        return jsonify({"success": False, "message": "缺少 'new_balance' 欄位"}), 400

    success, message = asset_manager.update_balance(account_id, new_balance)
    if success:
        return jsonify({"success": True, "message": message}), 200
    return jsonify({"success": False, "message": message}), 404

@app.route("/api/assets/<account_id>", methods=["DELETE"])
def delete_asset(account_id):
    success, message = asset_manager.delete_account(account_id)
    if success:
        return jsonify({"success": True, "message": message}), 200
    return jsonify({"success": False, "message": message}), 404

@app.route("/api/transfer", methods=["POST"])
def transfer_funds():
    data = request.get_json()
    source_id = data.get("source_id")
    dest_id = data.get("dest_id")
    amount = data.get("amount")

    if not all([source_id, dest_id, amount is not None]):
        return jsonify({"success": False, "message": "缺少必要欄位"}), 400

    success, message = asset_manager.transfer(source_id, dest_id, amount)
    
    if success:
        return jsonify({"success": True, "message": message}), 200
    else:
        return jsonify({"success": False, "message": message}), 400

# API - 預算與支出管理

@app.route("/api/budgets/categories", methods=["GET"])
def get_budget_categories():
    """
    獲取所有已設定的預算類別
    """
    categories = budget_manager.get_all_budget_categories()
    return jsonify({"success": True, "data": categories}), 200

@app.route("/api/budgets", methods=["POST"])
def set_budget():
    """
    設定某月某類別的預算
    - 接收 JSON 格式的資料
    """
    data = request.get_json()
    month = data.get("month")
    category = data.get("category")
    amount = data.get("amount")
    notes = data.get("notes", "")

    if not all([month, category, amount is not None]):
        return jsonify({"success": False, "message": "缺少必要欄位"}), 400

    success = budget_manager.set_budget(month, category, amount, notes)
    if success:
        return jsonify({"success": True, "message": "預算設定成功"}), 201
    else:
        return jsonify({"success": False, "message": "預算設定失敗"}), 500

@app.route("/api/budgets/<string:month>/<string:category>", methods=["DELETE"])
def delete_budget(month, category):
    """
    刪除某月某類別的預算
    - 透過 URL 路徑參數刪除
    """

    success = budget_manager.delete_budget(month, category)
    if success:
        return jsonify({"success": True, "message": "預算刪除成功"}), 200
    else:
        return jsonify({"success": False, "message": "預算刪除失敗，找不到預算"}), 404
    
@app.route("/api/months", methods=["GET"])
def get_available_months():
    """
    獲取所有有交易記錄的月份列表
    """
    months = budget_manager.get_all_transaction_months()
    return jsonify({"success": True, "data": sorted(months, reverse=True)}), 200

@app.route("/api/transactions", methods=["GET"])
def get_transactions():
    """
    獲取所有交易紀錄    
    """
    transactions_data = budget_manager.get_all_transactions()
    if transactions_data:
        return jsonify({"success": True, "data": transactions_data}), 200
    else:
        return jsonify({"success": False, "message": "沒有找到交易紀錄"}), 404
    
@app.route("/api/transactions", methods=["POST"])
def add_transaction():
    """
    新增一筆交易紀錄
    """
    data = request.get_json()
    date = data.get("date")
    item = data.get("item")
    amount = data.get("amount")
    transaction_type = data.get("type")
    budget_category = data.get("budget_category") # 接收新的欄位
    description = data.get("description", "") # 接收備註
    
    # 在這裡先驗證交易類型
    valid_types = ["expense", "income"]
    if transaction_type not in valid_types:
        return jsonify({"success": False, "message": "無效的交易類型"}), 400
    
    # 在這裡驗證必要欄位，並將其合併為一個檢查
    if not all([date, item, amount, transaction_type, budget_category]):
        return jsonify({"success": False, "message": "缺少必要欄位"}), 400

    # 直接將所有數據傳遞給管理器，由管理器處理邏輯
    success = budget_manager.add_transaction(
        date,
        item,
        amount,
        transaction_type,
        budget_category,
        description
    )

    if success:
        return jsonify({"success": True, "message": "交易新增成功"}), 201
    else:
        return jsonify({"success": False, "message": "交易新增失敗"}), 500

@app.route("/api/transactions/<string:transaction_id>", methods=["DELETE"])
def delete_transaction(transaction_id):
    """
    刪除一筆交易
    """
    success = budget_manager.delete_transaction(transaction_id)
    if success:
        return jsonify({"success": True, "message": "交易刪除成功"}), 200
    else:
        return jsonify({"success": False, "message": "交易刪除失敗，找不到該筆交易"}), 404

        
@app.route("/api/budgets/summary/<month>", methods=["GET"])
def get_monthly_summary(month):
    """
    獲取某月的消費總覽
    """
    # 獲取該月所有支出，並按類別彙總
    expense_totals = budget_manager.calculate_monthly_expenses(month)
    
    # 獲取該月所有預算
    budgets = budget_manager.budgets.get(month, {})

    # 建立一個包含所有類別的集合
    all_categories = set(expense_totals.keys()) | set(budgets.keys())

    response_data = []

    for category in all_categories:
        # 從支出總計中獲取金額，若無則為 0
        spent_amount = expense_totals.get(category, 0)
        
        # 從預算中獲取金額，若無則為 None
        budget_info = budgets.get(category)
        budget_amount = budget_info.get("amount") if budget_info else None
        
        # 計算剩餘金額，如果沒有預算則為 None
        remaining_amount = (budget_amount - spent_amount) if budget_amount is not None else None
        
        item = {
            "category": category,
            "spent": spent_amount,
            "budget": budget_amount,
            "remaining": remaining_amount
        }
        response_data.append(item)
    
    return jsonify({"success": True, "data": response_data})

# API - 財務目標管理

@app.route("/api/goals", methods=["POST"])
def add_goal():
    """
    新增目標
    - 接收 JSON 格式的資料
    """
    data = request.get_json()
    title = data.get("title")
    goal_type = data.get("goal_type")
    target_amount = data.get("target_amount")
    target_date = data.get("target_date")
    description = data.get("description", "")

    if not all([title, goal_type, target_amount, target_date]):
        return jsonify({"success": False, "message": "缺少必要欄位"}), 400

    success = goal_manager.add_goal(title, goal_type, target_amount, target_date, description)
    if success:
        return jsonify({"success": True, "message": "目標新增成功"}), 201
    else:
        return jsonify({"success": False, "message": "目標新增失敗"}), 500

@app.route("/api/goals/<goal_id>", methods=["PUT"])
def update_goal(goal_id):
    """
    更新目標的進度或任何其他資訊。
    - 透過 URL 傳入目標 ID
    - 接收 JSON 格式的資料，包含要更新的欄位 (例如: {"title": "新標題", "target_amount": 50000})
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "缺少要更新的資料"}), 400

    # 檢查是否只傳入 new_current_amount (為了向下相容)
    if "new_current_amount" in data and len(data) == 1:
        new_current_amount = data.get("new_current_amount")
        success = goal_manager.update_goal_progress(goal_id, new_current_amount)
    else:
        # 移除 new_current_amount 欄位，避免與新的 API 衝突
        if "new_current_amount" in data:
            data["current_amount"] = data.pop("new_current_amount")
        # 呼叫新的通用更新方法
        success = goal_manager.update_goal(goal_id, **data)

    if success:
        return jsonify({"success": True, "message": "目標更新成功"}), 200
    else:
        return jsonify({"success": False, "message": "目標更新失敗，找不到目標或資料無效"}), 404

@app.route("/api/goals/<goal_id>", methods=["DELETE"])
def delete_goal(goal_id):
    """
    刪除目標
    - 透過 URL 傳入目標 ID
    """
    success = goal_manager.delete_goal(goal_id)
    if success:
        return jsonify({"success": True, "message": "目標刪除成功"}), 200
    else:
        return jsonify({"success": False, "message": "目標刪除失敗，找不到目標"}), 404

@app.route("/api/goals", methods=["GET"])
def get_all_goals():
    """
    獲取所有財務目標資料
    """
    goals_data = goal_manager.get_all_goals()
    return jsonify({"success": True, "data": goals_data})

@app.route("/api/reports/monthly_expenses", methods=["GET"])
def get_monthly_expenses():
    """
    提供每月支出總額數據，以供前端圖表使用。
    """
    # 獲取請求中的 'month' 參數，如果沒有則使用當前月份
    year_month = request.args.get("month", datetime.now().strftime("%Y-%m"))

    # 呼叫 budget_manager 的方法來獲取彙總數據
    expense_data = budget_manager.calculate_monthly_expenses(year_month)

    # 將字典轉換成前端圖表所需的格式
    labels = list(expense_data.keys())
    data = list(expense_data.values())

    # 構建一個包含完整圖表數據的字典，並設定顏色
    chart_data = {
        "labels": labels,
        "datasets": [{
            "label": f"{year_month}月支出",
            "backgroundColor": ["#42A5F5", "#66BB6A", "#FFA726", "#26A69A", "#BDBDBD", "#7986CB", "#C0CA33"],
            "data": data
        }]
    }

    return jsonify({"success": True, "data": chart_data})

@app.route("/api/reports/asset_allocation", methods=["GET"])
def get_asset_allocation():
    """
    提供資產配置數據，以供前端圓餅圖使用。
    """
    totals = asset_manager.calculate_totals()
    
    # 排除 '總資產' 鍵，只保留帳戶類型
    labels = [key for key in totals.keys() if key != "總資產"]
    data = [totals[key] for key in labels]

    # 構建一個包含完整圖表數據的字典，並設定顏色
    chart_data = {
        "labels": labels,
        "datasets": [{
            "backgroundColor": ["#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0", "#9966FF", "#FF9F40"],
            "data": data
        }]
    }
    return jsonify({"success": True, "data": chart_data})

@app.route("/api/reports/income_expense_summary", methods=["GET"])
def get_income_expense_summary():
    """
    提供收入與支出總額數據，以供前端圖表使用。
    可選參數: month (YYYY-MM)
    """
    month = request.args.get("month")
    
    transactions = budget_manager.get_all_transactions()
    
    total_income = 0
    total_expense = 0

    for t in transactions:
        if month and not t.get("date", "").startswith(month):
            continue
        
        if t.get("type") == "income":
            total_income += t.get("amount", 0)
        elif t.get("type") == "expense":
            total_expense += t.get("amount", 0)

    chart_data = {
        "labels": ["收入", "支出"],
        "datasets": [{
            "label": f"{month if month else '總計'}收入與支出",
            "backgroundColor": ["#4CAF50", "#F44336"], # 綠色代表收入，紅色代表支出
            "data": [total_income, total_expense]
        }]
    }
    return jsonify({"success": True, "data": chart_data})

@app.route("/api/reports/overspending_warnings", methods=["GET"])
def get_overspending_warnings():
    """
    提供超支警告數據，以供前端顯示。
    可選參數: month (YYYY-MM)
    """
    month = request.args.get("month")
    warnings = budget_manager.check_over_warnings(month)
    return jsonify({"success": True, "data": warnings})

    return jsonify({"success": True, "data": chart_data})

@app.route("/api/reports/transactions_by_category_over_time", methods=["GET"])
def get_transactions_by_category_over_time():
    """
    提供按類別和時間聚合的交易數據，以供前端圖表使用。
    可選參數: start_date (YYYY-MM-DD), end_date (YYYY-MM-DD), interval (month, year)
    """
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    interval = request.args.get("interval", "month") # default to month

    transactions = budget_manager.get_all_transactions()

    # Filter transactions by date range if provided
    filtered_transactions = []
    for t in transactions:
        transaction_date = datetime.strptime(t["date"], "%Y-%m-%d")
        if start_date_str and transaction_date < datetime.strptime(start_date_str, "%Y-%m-%d"):
            continue
        if end_date_str and transaction_date > datetime.strptime(end_date_str, "%Y-%m-%d"):
            continue
        filtered_transactions.append(t)

    # Aggregate data
    aggregated_data = {}
    all_categories = set()
    all_periods = set()

    for t in filtered_transactions:
        category = t.get("budget_category", "未分類")
        amount = t.get("amount", 0)
        transaction_type = t.get("type")
        transaction_date = datetime.strptime(t["date"], "%Y-%m-%d")

        if interval == "month":
            period = transaction_date.strftime("%Y-%m")
        elif interval == "year":
            period = transaction_date.strftime("%Y")
        else:
            period = transaction_date.strftime("%Y-%m-%d") # Default to day if invalid interval

        all_categories.add(category)
        all_periods.add(period)

        if period not in aggregated_data:
            aggregated_data[period] = {}
        if category not in aggregated_data[period]:
            aggregated_data[period][category] = {"income": 0, "expense": 0}
        
        if transaction_type == "income":
            aggregated_data[period][category]["income"] += amount
        elif transaction_type == "expense":
            aggregated_data[period][category]["expense"] += amount

    # Sort periods chronologically
    sorted_periods = sorted(list(all_periods))
    sorted_categories = sorted(list(all_categories))

    datasets = []
    # For simplicity, let's create datasets for total income and total expense per period
    # A more complex chart might need datasets per category
    income_data = []
    expense_data = []

    for period in sorted_periods:
        period_income = 0
        period_expense = 0
        for category in sorted_categories:
            if period in aggregated_data and category in aggregated_data[period]:
                period_income += aggregated_data[period][category]["income"]
                period_expense += aggregated_data[period][category]["expense"]
        income_data.append(period_income)
        expense_data.append(period_expense)

    datasets.append({
        "label": "總收入",
        "backgroundColor": "#4CAF50",
        "data": income_data
    })
    datasets.append({
        "label": "總支出",
        "backgroundColor": "#F44336",
        "data": expense_data
    })

    chart_data = {
        "labels": sorted_periods,
        "datasets": datasets
    }

    return jsonify({"success": True, "data": chart_data})

    return jsonify({"success": True, "data": chart_data})

@app.route("/api/reports/goal_summary", methods=["GET"])
def get_goal_summary():
    """
    提供財務目標的總結數據，以供前端顯示。
    """
    goals = goal_manager.get_all_goals()
    
    total_target_amount = 0
    total_current_amount = 0
    completed_goals = 0
    active_goals = 0

    for goal_id, goal in goals.items():
        total_target_amount += goal.get("target_amount", 0)
        total_current_amount += goal.get("current_amount", 0)
        if goal.get("status") == "completed":
            completed_goals += 1
        else:
            active_goals += 1

    summary = {
        "total_goals": len(goals),
        "completed_goals": completed_goals,
        "active_goals": active_goals,
        "total_target_amount": total_target_amount,
        "total_current_amount": total_current_amount,
        "overall_progress_percentage": (total_current_amount / total_target_amount * 100) if total_target_amount > 0 else 0
    }
    return jsonify({"success": True, "data": summary})

# if __name__ == "__main__":
#     app.run(debug=True, host="0.0.0.0", port=5000)