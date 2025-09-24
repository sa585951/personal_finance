from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import Flask, jsonify, request, redirect, url_for
from flask_cors import CORS
from sqlalchemy import select, func
from linebot.exceptions import InvalidSignatureError
import os # Import os
import requests # Import requests
import jwt

# 匯入重構後的核心類別和資料庫引擎
from models.asset_manager import AssetManager
from models.budget_manager import BudgetManager
from models.goal_manager import GoalManager
from models.linebot.manager import LineBotManager
from models.app_state import AppStateManager
from models.database import engine 
from models.schema import budget_categories_table, transactions_table 
from models.user_manager import UserManager # Import UserManager

LINE_CHANNEL_ID = os.getenv("LINE_LOGIN_CHANNEL_ID")
LINE_CHANNEL_SECRET = os.getenv("LINE_LOGIN_CHANNEL_SECRET")
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173") # 預設為 Vite 的開發伺服器

if not all([LINE_CHANNEL_ID, LINE_CHANNEL_SECRET, JWT_SECRET_KEY]):
    raise EnvironmentError("LINE_LOGIN_CHANNEL_ID, LINE_LOGIN_CHANNEL_SECRET, or JWT_SECRET_KEY 環境變數未設定，請檢查 .env 檔案。")

if not BACKEND_BASE_URL:
    raise EnvironmentError("BACKEND_BASE_URL 環境變數未設定，請檢查 .env 檔案。")

# 實例化 Flask 應用程式
app = Flask(__name__)
CORS(app) # 簡化 CORS 設定，允許所有來源

def token_required(f):
    """Token 驗證裝飾器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            # 格式為 'Bearer <token>'
            token = request.headers['Authorization'].split(' ')[1]
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
            current_user_id = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid!'}), 401

        # 將 user_id 傳遞給路由函式
        return f(current_user_id, *args, **kwargs)

    return decorated

# 實例化 Manager 類別，它們將在整個應用程式中被重複使用
app_state = AppStateManager()
asset_manager = AssetManager()
budget_manager = BudgetManager()
goal_manager = GoalManager()
user_manager = UserManager() # Instantiate UserManager
linebot_manager = LineBotManager(budget_manager, asset_manager, goal_manager, app_state, user_manager)

@app.route("/")
def home():
    """根路由，回傳歡迎訊息"""
    return "歡迎來到個人財務管理系統的後端 API！"

# --- API - 資產管理 ---

@app.route("/api/assets", methods=["GET"])
@token_required
def get_assets(current_user_id):
    assets = asset_manager.get_all_assets(user_id=current_user_id)
    return jsonify({"success": True, "data": assets}), 200

@app.route("/api/assets", methods=["POST"])
@token_required
def add_asset(current_user_id):
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "缺少資料"}), 400
    
    bank_name = data.get("bank_name")
    account_type = data.get("account_type")
    balance = data.get("balance")

    if not all([bank_name, account_type, balance is not None]):
        return jsonify({"success": False, "message": "缺少必要欄位"}), 400

    success, message = asset_manager.add_account(current_user_id, bank_name, account_type, balance)
    if success:
        return jsonify({"success": True, "message": message}), 201
    else:
        return jsonify({"success": False, "message": message}), 409

@app.route("/api/assets/<string:account_key>", methods=["PUT"])
@token_required
def update_asset_balance(current_user_id, account_key):
    data = request.get_json()
    new_balance = data.get('new_balance')
    if new_balance is None:
        return jsonify({"success": False, "message": "缺少 'new_balance' 欄位"}), 400

    success, message = asset_manager.update_balance(current_user_id, account_key, new_balance)
    if success:
        return jsonify({"success": True, "message": message}), 200
    return jsonify({"success": False, "message": message}), 404

@app.route("/api/assets/<string:account_key>", methods=["DELETE"])
@token_required
def delete_asset(current_user_id, account_key):
    success, message = asset_manager.delete_account(current_user_id, account_key)
    if success:
        return jsonify({"success": True, "message": message}), 200
    return jsonify({"success": False, "message": message}), 404

@app.route("/api/transfer", methods=["POST"])
@token_required
def transfer_funds(current_user_id):
    data = request.get_json()
    source_id = data.get("source_id")
    dest_id = data.get("dest_id")
    amount = data.get("amount")

    if not all([source_id, dest_id, amount is not None]):
        return jsonify({"success": False, "message": "缺少必要欄位"}), 400

    success, message = asset_manager.transfer(current_user_id, source_id, dest_id, amount)
    
    if success:
        return jsonify({"success": True, "message": message}), 200
    else:
        return jsonify({"success": False, "message": message}), 400

# --- API - 預算與支出管理 ---

@app.route("/api/budgets/categories", methods=["GET"])
@token_required
def get_budget_categories(current_user_id):
    categories = budget_manager.get_all_budget_categories(user_id=current_user_id)
    return jsonify({"success": True, "data": categories}), 200

@app.route("/api/budgets", methods=["POST"])
@token_required
def set_budget(current_user_id):
    data = request.get_json()
    month = data.get("month")
    category = data.get("category")
    amount = data.get("amount")
    notes = data.get("notes", "")

    if not all([month, category, amount is not None]):
        return jsonify({"success": False, "message": "缺少必要欄位"}), 400

    success, message = budget_manager.set_budget(current_user_id, month, category, amount, notes)
    if success:
        return jsonify({"success": True, "message": "預算設定成功"}), 201
    else:
        return jsonify({"success": False, "message": message}), 500

@app.route("/api/budgets/<string:month>/<string:category>", methods=["DELETE"])
@token_required
def delete_budget(current_user_id, month, category):
    success, message = budget_manager.delete_budget(current_user_id, month, category)
    if success:
        return jsonify({"success": True, "message": message}), 200
    else:
        return jsonify({"success": False, "message": message}), 404
    
@app.route("/api/months", methods=["GET"])
@token_required
def get_available_months(current_user_id):
    months = budget_manager.get_all_transaction_months(user_id=current_user_id)
    return jsonify({"success": True, "data": sorted(months, reverse=True)}), 200

@app.route("/api/transactions", methods=["GET"])
@token_required
def get_transactions(current_user_id):
    transactions_data = budget_manager.get_all_transactions(user_id=current_user_id)
    return jsonify({"success": True, "data": transactions_data}), 200
    
@app.route("/api/transactions", methods=["POST"])
@token_required
def add_transaction(current_user_id):
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
        current_user_id, date, item, amount, transaction_type, budget_category, description
    )

    if success:
        return jsonify({"success": True, "message": message}), 201
    else:
        return jsonify({"success": False, "message": message}), 500

@app.route("/api/transactions/<string:transaction_id>", methods=["DELETE"])
@token_required
def delete_transaction(current_user_id, transaction_id):
    # UUID 是字串，所以不需要類型轉換
    success, message = budget_manager.delete_transaction(current_user_id, transaction_id)
    if success:
        return jsonify({"success": True, "message": message}), 200
    else:
        return jsonify({"success": False, "message": message}), 404

@app.route("/api/budgets/summary/<string:month>", methods=["GET"])
@token_required
def get_monthly_summary(current_user_id, month):
    # 1. 獲取該月所有預算
    budget_stmt = select(budget_categories_table).where(
        budget_categories_table.c.user_id == current_user_id, 
        budget_categories_table.c.month == month
    )
    with engine.connect() as conn:
        budgets_result = conn.execute(budget_stmt)
        budgets = {row.category_name: row.amount for row in budgets_result}

    # 2. 獲取該月所有支出
    expense_totals = budget_manager.calculate_monthly_expenses(current_user_id, month)
    
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
@token_required
def get_all_goals(current_user_id):
    goals_data = goal_manager.get_all_goals(user_id=current_user_id)
    return jsonify({"success": True, "data": goals_data})

@app.route("/api/goals", methods=["POST"])
@token_required
def add_goal(current_user_id):
    data = request.get_json()
    title = data.get("title")
    type = data.get("type") # 前端傳來的 type
    target_amount = data.get("target_amount")
    target_date = data.get("target_date")
    description = data.get("description", "")

    if not all([title, type, target_amount, target_date]):
        return jsonify({"success": False, "message": "缺少必要欄位"}), 400

    success, result = goal_manager.add_goal(current_user_id, title, type, target_amount, target_date, description)
    if success:
        return jsonify({"success": True, "message": "目標新增成功", "data": result}), 201
    else:
        return jsonify({"success": False, "message": result}), 500

@app.route("/api/goals/<int:goal_id>", methods=["PUT"])
@token_required
def update_goal(current_user_id, goal_id):
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "缺少要更新的資料"}), 400

    success, message = goal_manager.update_goal(current_user_id, goal_id, **data)

    if success:
        return jsonify({"success": True, "message": message}), 200
    else:
        return jsonify({"success": False, "message": message}), 404

@app.route("/api/goals/<int:goal_id>", methods=["DELETE"])
@token_required
def delete_goal(current_user_id, goal_id):
    success, message = goal_manager.delete_goal(current_user_id, goal_id)
    if success:
        return jsonify({"success": True, "message": message}), 200
    else:
        return jsonify({"success": False, "message": message}), 404

# --- API - 報告 ---

@app.route("/api/reports/monthly_expenses", methods=["GET"])
@token_required
def get_monthly_expenses(current_user_id):
    year_month = request.args.get("month", datetime.now().strftime("%Y-%m"))
    expense_data = budget_manager.calculate_monthly_expenses(current_user_id, year_month)
    
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
@token_required
def get_asset_allocation(current_user_id):
    totals = asset_manager.calculate_totals(user_id=current_user_id)
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
@token_required
def get_income_expense_summary(current_user_id):
    month = request.args.get("month")
    
    stmt = select(transactions_table.c.type, func.sum(transactions_table.c.amount).label("total")) \
        .where(transactions_table.c.user_id == current_user_id)
    
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
@token_required
def get_transactions_by_category_over_time(current_user_id):
    interval = request.args.get("interval", "month") # Default to 'month'
    chart_data = budget_manager.get_transactions_by_category_over_time(current_user_id, interval)
    return jsonify({"success": True, "data": chart_data})


@app.route("/api/reports/overspending_warnings", methods=["GET"])
@token_required
def get_overspending_warnings(current_user_id):
    month = request.args.get("month")
    warnings = budget_manager.check_over_warnings(current_user_id, month)
    return jsonify({"success": True, "data": warnings})

@app.route("/api/reports/goal_summary", methods=["GET"])
@token_required
def get_goal_summary(current_user_id):
    summary = goal_manager.calculate_goal_summary(user_id=current_user_id)
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

@app.route("/line-login-callback", methods=["GET"])
def line_login_callback():
    code = request.args.get('code')
    state = request.args.get('state')
    # 這裡可以加入 state 驗證，防止 CSRF 攻擊

    if not code:
        return jsonify({"success": False, "message": "授權碼遺失"}), 400

    # 1. 向 Line 交換 Access Token 和 ID Token
    token_url = "https://api.line.me/oauth2/v2.1/token"
    redirect_uri = f"{BACKEND_BASE_URL}/line-login-callback"

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri, # 使用 BACKEND_BASE_URL
        'client_id': LINE_CHANNEL_ID,
        'client_secret': LINE_CHANNEL_SECRET
    }
    
    try:
        response = requests.post(token_url, headers=headers, data=data)
        response.raise_for_status() # 如果請求失敗，會拋出 HTTPError
        token_info = response.json()
        access_token = token_info.get('access_token')
        id_token = token_info.get('id_token')

        if not id_token:
            return jsonify({"success": False, "message": "未取得 ID Token"}), 400

        # 2. 驗證 ID Token 並獲取使用者資訊
        decoded_id_token = jwt.decode(
            id_token,
            LINE_CHANNEL_SECRET, # 使用 Channel Secret 作為驗證金鑰
            algorithms=['HS256'],
            audience=LINE_CHANNEL_ID,
            issuer='https://access.line.me'
        )

        user_id = decoded_id_token.get('sub') # 'sub' 欄位是 Line 的 user_id
        display_name = decoded_id_token.get('name')

        if not user_id:
            return jsonify({"success": False, "message": "無法從 ID Token 獲取使用者 ID"}), 400

        # 3. 確保使用者存在於資料庫
        user = user_manager.get_or_create_user(user_id, display_name)

        # 4. 產生應用程式自己的 JWT
        payload = {
            'user_id': user['user_id'],
            'name': user['display_name'], # 將使用者名稱加入 payload
            'exp': datetime.now(timezone.utc) + timedelta(days=1)  # Token 有效期為 1 天
        }
        app_token = jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")

        # 5. 重定向到前端的回呼 URL，並附上 token
        return redirect(f"{FRONTEND_BASE_URL}/auth-callback?token={app_token}")

    except requests.exceptions.RequestException as e:
        print(f"Line Token Exchange Error: {e}")
        return jsonify({"success": False, "message": f"Line 認證失敗: {e}"}), 500
    except jwt.PyJWTError as e:
        print(f"ID Token Verification Error: {e}")
        return jsonify({"success": False, "message": f"ID Token 驗證失敗: {e}"}), 500
    except Exception as e:
        print(f"Unhandled Line Login Callback Error: {e}")
        return jsonify({"success": False, "message": f"登入處理失敗: {e}"}), 500

if __name__ == "__main__":
    # 在生產環境中，應使用 Gunicorn 或其他 WSGI 伺服器
    # 例如: gunicorn --bind 0.0.0.0:5000 web_app:app
    app.run(debug=True, host="0.0.0.0", port=5000)
