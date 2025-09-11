from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy import select, func
from linebot.exceptions import InvalidSignatureError

# 匯入重構後的核心類別和資料庫引擎
from models.asset_manager import AssetManager
from models.budget_manager import BudgetManager
from models.goal_manager import GoalManager
from models.linebot.manager import LineBotManager
from models.app_state import AppStateManager
from models.database import engine 
from models.schema import budget_categories_table, transactions_table 

# 實例化 Flask 應用程式
app = Flask(__name__)
CORS(app) # 簡化 CORS 設定，允許所有來源

# 實例化 Manager 類別，它們將在整個應用程式中被重複使用
app_state = AppStateManager()
asset_manager = AssetManager()
budget_manager = BudgetManager()
goal_manager = GoalManager()
linebot_manager = LineBotManager(budget_manager, asset_manager, app_state)

@app.route("/")
def home():
    """根路由，回傳歡迎訊息"""
    return "歡迎來到個人財務管理系統的後端 API！"

# --- API - 資產管理 ---

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
    balance = data.get("balance")

    if not all([bank_name, account_type, balance is not None]):
        return jsonify({"success": False, "message": "缺少必要欄位"}), 400

    success, message = asset_manager.add_account(bank_name, account_type, balance)
    if success:
        return jsonify({"success": True, "message": message}), 201
    else:
        return jsonify({"success": False, "message": message}), 409

@app.route("/api/assets/<string:account_key>", methods=["PUT"])
def update_asset_balance(account_key):
    data = request.get_json()
    new_balance = data.get('new_balance')
    if new_balance is None:
        return jsonify({"success": False, "message": "缺少 'new_balance' 欄位"}), 400

    success, message = asset_manager.update_balance(account_key, new_balance)
    if success:
        return jsonify({"success": True, "message": message}), 200
    return jsonify({"success": False, "message": message}), 404

@app.route("/api/assets/<string:account_key>", methods=["DELETE"])
def delete_asset(account_key):
    success, message = asset_manager.delete_account(account_key)
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

# --- API - 預算與支出管理 ---

@app.route("/api/budgets/categories", methods=["GET"])
def get_budget_categories():
    categories = budget_manager.get_all_budget_categories()
    return jsonify({"success": True, "data": categories}), 200

@app.route("/api/budgets", methods=["POST"])
def set_budget():
    data = request.get_json()
    month = data.get("month")
    category = data.get("category")
    amount = data.get("amount")
    notes = data.get("notes", "")

    if not all([month, category, amount is not None]):
        return jsonify({"success": False, "message": "缺少必要欄位"}), 400

    success, message = budget_manager.set_budget(month, category, amount, notes)
    if success:
        return jsonify({"success": True, "message": "預算設定成功"}), 201
    else:
        return jsonify({"success": False, "message": message}), 500

@app.route("/api/budgets/<string:month>/<string:category>", methods=["DELETE"])
def delete_budget(month, category):
    success, message = budget_manager.delete_budget(month, category)
    if success:
        return jsonify({"success": True, "message": message}), 200
    else:
        return jsonify({"success": False, "message": message}), 404
    
@app.route("/api/months", methods=["GET"])
def get_available_months():
    months = budget_manager.get_all_transaction_months()
    return jsonify({"success": True, "data": sorted(months, reverse=True)}), 200

@app.route("/api/transactions", methods=["GET"])
def get_transactions():
    transactions_data = budget_manager.get_all_transactions()
    return jsonify({"success": True, "data": transactions_data}), 200
    
@app.route("/api/transactions", methods=["POST"])
def add_transaction():
    data = request.get_json()
    date = data.get("date")
    item = data.get("item") # 前端對應到 category
    amount = data.get("amount")
    transaction_type = data.get("type")
    budget_category = data.get("budget_category")
    description = data.get("description", "")
    
    if not all([date, item, amount, transaction_type, budget_category]):
        return jsonify({"success": False, "message": "缺少必要欄位"}), 400

    success, message = budget_manager.add_transaction(
        date, item, amount, transaction_type, budget_category, description
    )

    if success:
        return jsonify({"success": True, "message": message}), 201
    else:
        return jsonify({"success": False, "message": message}), 500

@app.route("/api/transactions/<string:transaction_id>", methods=["DELETE"])
def delete_transaction(transaction_id):
    # UUID 是字串，所以不需要類型轉換
    success, message = budget_manager.delete_transaction(transaction_id)
    if success:
        return jsonify({"success": True, "message": message}), 200
    else:
        return jsonify({"success": False, "message": message}), 404

@app.route("/api/budgets/summary/<string:month>", methods=["GET"])
def get_monthly_summary(month):
    # 1. 獲取該月所有預算
    budget_stmt = select(budget_categories_table).where(budget_categories_table.c.month == month)
    with engine.connect() as conn:
        budgets_result = conn.execute(budget_stmt)
        budgets = {row.category_name: row.amount for row in budgets_result}

    # 2. 獲取該月所有支出
    expense_totals = budget_manager.calculate_monthly_expenses(month)
    
    # 3. 合併資料
    all_categories = set(expense_totals.keys()) | set(budgets.keys())
    response_data = []
    for category in all_categories:
        spent = expense_totals.get(category, 0)
        budget = budgets.get(category)
        item = {
            "category": category,
            "spent": spent,
            "budget": budget,
            "remaining": (budget - spent) if budget is not None else None
        }
        response_data.append(item)
    
    return jsonify({"success": True, "data": response_data})

# --- API - 財務目標管理 ---

@app.route("/api/goals", methods=["GET"])
def get_all_goals():
    goals_data = goal_manager.get_all_goals()
    return jsonify({"success": True, "data": goals_data})

@app.route("/api/goals", methods=["POST"])
def add_goal():
    data = request.get_json()
    title = data.get("title")
    goal_type = data.get("type") # 前端傳來的 goal_type
    target_amount = data.get("target_amount")
    target_date = data.get("target_date")
    description = data.get("description", "")

    if not all([title, goal_type, target_amount, target_date]):
        return jsonify({"success": False, "message": "缺少必要欄位"}), 400

    success, result = goal_manager.add_goal(title, goal_type, target_amount, target_date, description)
    if success:
        return jsonify({"success": True, "message": "目標新增成功", "data": result}), 201
    else:
        return jsonify({"success": False, "message": result}), 500

@app.route("/api/goals/<int:goal_id>", methods=["PUT"])
def update_goal(goal_id):
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "缺少要更新的資料"}), 400

    success, message = goal_manager.update_goal(goal_id, **data)

    if success:
        return jsonify({"success": True, "message": message}), 200
    else:
        return jsonify({"success": False, "message": message}), 404

@app.route("/api/goals/<int:goal_id>", methods=["DELETE"])
def delete_goal(goal_id):
    success, message = goal_manager.delete_goal(goal_id)
    if success:
        return jsonify({"success": True, "message": message}), 200
    else:
        return jsonify({"success": False, "message": message}), 404

# --- API - 報告 ---

@app.route("/api/reports/monthly_expenses", methods=["GET"])
def get_monthly_expenses():
    year_month = request.args.get("month", datetime.now().strftime("%Y-%m"))
    expense_data = budget_manager.calculate_monthly_expenses(year_month)
    
    chart_data = {
        "labels": list(expense_data.keys()),
        "datasets": [{
            "label": f"{year_month}月支出",
            "backgroundColor": ["#42A5F5", "#66BB6A", "#FFA726", "#26A69A", "#BDBDBD", "#7986CB", "#C0CA33"],
            "data": list(expense_data.values())
        }]
    }
    return jsonify({"success": True, "data": chart_data})

@app.route("/api/reports/asset_allocation", methods=["GET"])
def get_asset_allocation():
    # 這個方法需要在 AssetManager 中重新實現
    totals = asset_manager.calculate_totals()
    labels = [key for key in totals.keys() if key != "總資產"]
    data = [totals[key] for key in labels]

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
    month = request.args.get("month")
    
    stmt = select(transactions_table.c.type, func.sum(transactions_table.c.amount).label("total"))
    if month:
        stmt = stmt.where(func.to_char(transactions_table.c.date, 'YYYY-MM') == month)
    stmt = stmt.group_by(transactions_table.c.type)

    income = 0
    expense = 0
    with engine.connect() as conn:
        result = conn.execute(stmt)
        for row in result:
            if row.type == 'income':
                income = row.total or 0
            elif row.type == 'expense':
                expense = row.total or 0

    chart_data = {
        "labels": ["收入", "支出"],
        "datasets": [{
            "label": f"{month if month else '總計'}收入與支出",
            "backgroundColor": ["#4CAF50", "#F44336"],
            "data": [float(income), float(expense)]
        }]
    }
    return jsonify({"success": True, "data": chart_data})

@app.route("/api/reports/transactions_by_category_over_time", methods=["GET"])
def get_transactions_by_category_over_time():
    interval = request.args.get("interval", "month") # Default to 'month'
    chart_data = budget_manager.get_transactions_by_category_over_time(interval)
    return jsonify({"success": True, "data": chart_data})


@app.route("/api/reports/overspending_warnings", methods=["GET"])
def get_overspending_warnings():
    month = request.args.get("month")
    warnings = budget_manager.check_over_warnings(month)
    return jsonify({"success": True, "data": warnings})

@app.route("/api/reports/goal_summary", methods=["GET"])
def get_goal_summary():
    summary = goal_manager.calculate_goal_summary()
    return jsonify({"success": True, "data": summary})

@app.route("/line-webhook", methods=["POST"])
def line_webhook():
    """Line Bot Webhook 端點"""
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)

    try:

        # 應用層處理冷啟動
        if app_state.is_cold_start():
            print("系統冷啟動期間，webhook 請求可能不穩定")
        
        linebot_manager.handler.handle(body, signature)
        return 'OK', 200

    except Exception as e:
        print(f"LINE Webhook error: {e}")
        return 'Internal Server Error', 500

if __name__ == "__main__":
    # 在生產環境中，應使用 Gunicorn 或其他 WSGI 伺服器
    # 例如: gunicorn --bind 0.0.0.0:5000 web_app:app
    app.run(debug=True, host="0.0.0.0", port=5000)
