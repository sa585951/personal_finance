from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import Flask, jsonify, request, redirect, url_for
from flask_cors import CORS
from sqlalchemy import select, func
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage
import os
import requests
import jwt

# 匯入重構後的核心類別和資料庫引擎
from models.asset_manager import AssetManager
from models.budget_manager import BudgetManager
from models.goal_manager import GoalManager
from models.linebot.manager import LineBotManager
from models.app_state import AppStateManager
from models.database import db_session 
from models.schema import budget_categories_table, transactions_table 
from models.user_manager import UserManager

LINE_CHANNEL_ID = os.getenv("LINE_LOGIN_CHANNEL_ID")
LINE_CHANNEL_SECRET = os.getenv("LINE_LOGIN_CHANNEL_SECRET")
VITE_BACKEND_BASE_URL = os.getenv("VITE_BACKEND_BASE_URL")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")

if not all([LINE_CHANNEL_ID, LINE_CHANNEL_SECRET, JWT_SECRET_KEY, VITE_BACKEND_BASE_URL]):
    raise EnvironmentError("缺少必要的環境變數，請檢查 .env 檔案。 সন")

# 實例化 Flask 應用程式
app = Flask(__name__)
CORS(
    app,
    origins=["https://personal-finance-gilt.vercel.app", "http://localhost:5173"],
    supports_credentials=True
)

# 實例化 Manager
asset_manager = AssetManager(db_session)
budget_manager = BudgetManager(db_session)
goal_manager = GoalManager(db_session)
user_manager = UserManager(db_session)

@app.teardown_appcontext
def shutdown_session(exception=None):
    """請求結束後自動關閉 session"""
    try:
        if exception:
            db_session.rollback()
    except Exception as e:
        app.logger.error(f"Session rollback failed: {e}")
    finally:
        db_session.remove()

def token_required(f):
    """Token 驗證裝飾器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
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

        return f(current_user_id, *args, **kwargs)
    return decorated

app_state = AppStateManager()
linebot_manager = LineBotManager(app_state, db_session)


@app.route("/")
def home():
    """根路由，回傳歡迎訊息"""
    return "歡迎來到個人財務管理系統的後端 API！"

# --- API - 資產管理 ---

@app.route("/api/assets", methods=["GET"])
@token_required
def get_assets(current_user_id):
    try:
        assets = asset_manager.get_all_assets(current_user_id)
        return jsonify({"success": True, "data": assets}), 200
    except Exception as e:
        app.logger.error(f"Error in get_assets: {e}")
        return jsonify({"success": False, "message": "伺服器內部錯誤"}), 500

@app.route("/api/assets", methods=["POST"])
@token_required
def add_asset(current_user_id):
    data = request.get_json()
    if not data or not all(k in data for k in ["bank_name", "account_type", "balance"]):
        return jsonify({"success": False, "message": "缺少必要欄位"}), 400
    
    try:
        success, message = asset_manager.add_account(
            current_user_id, data["bank_name"], data["account_type"], data["balance"]
        )
        if success:
            db_session.commit()
        return jsonify({"success": success, "message": message}), 201
    except Exception as e:
        app.logger.error(f"Error in add_asset: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/assets/<string:account_key>", methods=["PUT"])
@token_required
def update_asset_balance(current_user_id, account_key):
    data = request.get_json()
    if not data or 'new_balance' not in data:
        return jsonify({"success": False, "message": "缺少 'new_balance' 欄位"}), 400

    try:
        success, message = asset_manager.update_balance(current_user_id, account_key, data['new_balance'])
        if success:
            db_session.commit()
        return jsonify({"success": success, "message": message}), 200
    except Exception as e:
        app.logger.error(f"Error in update_asset_balance: {e}")
        return jsonify({"success": False, "message": str(e)}), 404

@app.route("/api/assets/<string:account_key>", methods=["DELETE"])
@token_required
def delete_asset(current_user_id, account_key):
    try:
        success, message = asset_manager.delete_account(current_user_id, account_key)
        if success:
            db_session.commit()
        return jsonify({"success": success, "message": message}), 200
    except Exception as e:
        app.logger.error(f"Error in delete_asset: {e}")
        return jsonify({"success": False, "message": str(e)}), 404

@app.route("/api/transfer", methods=["POST"])
@token_required
def transfer_funds(current_user_id):
    data = request.get_json()
    if not data or not all(k in data for k in ["source_id", "dest_id", "amount"]):
        return jsonify({"success": False, "message": "缺少必要欄位"}), 400

    try:
        success, message = asset_manager.transfer(current_user_id, data["source_id"], data["dest_id"], data["amount"])
        if success:
            db_session.commit()
        return jsonify({"success": success, "message": message}), 200
    except Exception as e:
        app.logger.error(f"Error in transfer_funds: {e}")
        return jsonify({"success": False, "message": str(e)}), 400

# --- API - 預算與支出管理 ---

@app.route("/api/budgets/categories", methods=["GET"])
@token_required
def get_budget_categories(current_user_id):
    try:
        categories = budget_manager.get_all_budget_categories(current_user_id)
        return jsonify({"success": True, "data": categories}), 200
    except Exception as e:
        app.logger.error(f"Error in get_budget_categories: {e}")
        return jsonify({"success": False, "message": "伺服器內部錯誤"}), 500

@app.route("/api/budgets", methods=["POST"])
@token_required
def set_budget(current_user_id):
    data = request.get_json()
    if not data or not all(k in data for k in ["month", "category", "amount"]):
        return jsonify({"success": False, "message": "缺少必要欄位"}), 400
    
    try:
        success, message = budget_manager.set_budget(
            current_user_id, data["month"], data["category"], data["amount"], data.get("notes", "")
        )
        if success:
            db_session.commit()
        return jsonify({"success": success, "message": message}), 201
    except Exception as e:
        app.logger.error(f"Error in set_budget: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
@app.route("/api/budgets/<string:month>/<string:category>", methods=["DELETE"])
@token_required
def delete_budget(current_user_id, month, category):
    try:
        success, message = budget_manager.delete_budget(current_user_id, month, category)
        if success:
            db_session.commit()
        return jsonify({"success": success, "message": message}), 200
    except Exception as e:
        app.logger.error(f"Error in delete_budget: {e}")
        return jsonify({"success": False, "message": str(e)}), 404
    
@app.route("/api/months", methods=["GET"])
@token_required
def get_available_months(current_user_id):
    try:
        months = budget_manager.get_all_transaction_months(current_user_id)
        return jsonify({"success": True, "data": sorted(months, reverse=True)}), 200
    except Exception as e:
        app.logger.error(f"Error in get_available_months: {e}")
        return jsonify({"success": False, "message": "伺服器內部錯誤"}), 500

@app.route("/api/transactions", methods=["GET"])
@token_required
def get_transactions(current_user_id):
    try:
        transactions_data = budget_manager.get_all_transactions(current_user_id)
        return jsonify({"success": True, "data": transactions_data}), 200
    except Exception as e:
        app.logger.error(f"Error in get_transactions: {e}")
        return jsonify({"success": False, "message": "伺服器內部錯誤"}), 500
    
@app.route("/api/transactions", methods=["POST"])
@token_required
def add_transaction(current_user_id):
    data = request.get_json()
    required_fields = ["date", "item", "amount", "type", "budget_category"]
    if not data or not all(k in data for k in required_fields):
        return jsonify({"success": False, "message": "缺少必要欄位"}), 400

    try:
        success, message = budget_manager.add_transaction(
            current_user_id, data["date"], data["item"], data["amount"], 
            data["type"], data["budget_category"], data.get("description", "")
        )
        if success:
            db_session.commit()
        return jsonify({"success": success, "message": message}), 201
    except Exception as e:
        app.logger.error(f"Error in add_transaction: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/transactions/<string:transaction_id>", methods=["DELETE"])
@token_required
def delete_transaction(current_user_id, transaction_id):
    try:
        success, message = budget_manager.delete_transaction(current_user_id, transaction_id)
        if success:
            db_session.commit()
        return jsonify({"success": success, "message": message}), 200
    except Exception as e:
        app.logger.error(f"Error in delete_transaction: {e}")
        return jsonify({"success": False, "message": str(e)}), 404

@app.route("/api/budgets/summary/<string:month>", methods=["GET"])
@token_required
def get_monthly_summary(current_user_id, month):
    try:
        budget_stmt = select(budget_categories_table).where(
            budget_categories_table.c.user_id == current_user_id, 
            budget_categories_table.c.month == month
        )
        budgets_result = db_session.execute(budget_stmt)
        budgets = {row.category_name: row.amount for row in budgets_result}

        expense_totals = budget_manager.calculate_monthly_expenses(current_user_id, month)
        
        all_categories = set(expense_totals.keys()) | set(budgets.keys())
        response_data = [
            {
                "category": category,
                "spent": expense_totals.get(category, 0),
                "budget": budgets.get(category),
                "remaining": (budgets.get(category) - expense_totals.get(category, 0)) if budgets.get(category) is not None else None
            }
            for category in all_categories
        ]
        return jsonify({"success": True, "data": response_data})
    except Exception as e:
        app.logger.error(f"Error in get_monthly_summary: {e}")
        return jsonify({"success": False, "message": "伺服器內部錯誤"}), 500

# --- API - 財務目標管理 ---

@app.route("/api/goals", methods=["GET"])
@token_required
def get_all_goals(current_user_id):
    try:
        goals_data = goal_manager.get_all_goals(current_user_id)
        return jsonify({"success": True, "data": goals_data})
    except Exception as e:
        app.logger.error(f"Error in get_all_goals: {e}")
        return jsonify({"success": False, "message": "伺服器內部錯誤"}), 500

@app.route("/api/goals", methods=["POST"])
@token_required
def add_goal(current_user_id):
    data = request.get_json()
    required_fields = ["title", "type", "target_amount", "target_date"]
    if not data or not all(k in data for k in required_fields):
        return jsonify({"success": False, "message": "缺少必要欄位"}), 400

    try:
        success, result = goal_manager.add_goal(
            current_user_id, data["title"], data["type"], data["target_amount"], 
            data["target_date"], data.get("description", "")
        )
        if success:
            db_session.commit()
        return jsonify({"success": success, "message": "目標新增成功", "data": result}), 201
    except Exception as e:
        app.logger.error(f"Error in add_goal: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/goals/<int:goal_id>", methods=["PUT"])
@token_required
def update_goal(current_user_id, goal_id):
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "缺少要更新的資料"}), 400

    try:
        success, message = goal_manager.update_goal(current_user_id, goal_id, **data)
        if success:
            db_session.commit()
        return jsonify({"success": success, "message": message}), 200
    except Exception as e:
        app.logger.error(f"Error in update_goal: {e}")
        return jsonify({"success": False, "message": str(e)}), 404

@app.route("/api/goals/<int:goal_id>", methods=["DELETE"])
@token_required
def delete_goal(current_user_id, goal_id):
    try:
        success, message = goal_manager.delete_goal(current_user_id, goal_id)
        if success:
            db_session.commit()
        return jsonify({"success": success, "message": message}), 200
    except Exception as e:
        app.logger.error(f"Error in delete_goal: {e}")
        return jsonify({"success": False, "message": str(e)}), 404

# --- API - 報告 ---

@app.route("/api/reports/monthly_expenses", methods=["GET"])
@token_required
def get_monthly_expenses(current_user_id):
    year_month = request.args.get("month", datetime.now().strftime("%Y-%m"))
    try:
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
    except Exception as e:
        app.logger.error(f"Error in get_monthly_expenses: {e}")
        return jsonify({"success": False, "message": "伺服器內部錯誤"}), 500

@app.route("/api/reports/asset_allocation", methods=["GET"])
@token_required
def get_asset_allocation(current_user_id):
    try:
        totals = asset_manager.calculate_totals(current_user_id)
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
    except Exception as e:
        app.logger.error(f"Error in get_asset_allocation: {e}")
        return jsonify({"success": False, "message": "伺服器內部錯誤"}), 500

@app.route("/api/reports/income_expense_summary", methods=["GET"])
@token_required
def get_income_expense_summary(current_user_id):
    month = request.args.get("month")
    try:
        stmt = select(transactions_table.c.type, func.sum(transactions_table.c.amount).label("total")) \
            .where(transactions_table.c.user_id == current_user_id)
        if month:
            stmt = stmt.where(func.to_char(transactions_table.c.date, 'YYYY-MM') == month)
        stmt = stmt.group_by(transactions_table.c.type)

        income, expense = 0, 0
        result = db_session.execute(stmt)
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
    except Exception as e:
        app.logger.error(f"Error in get_income_expense_summary: {e}")
        return jsonify({"success": False, "message": "伺服器內部錯誤"}), 500

@app.route("/api/reports/transactions_by_category_over_time", methods=["GET"])
@token_required
def get_transactions_by_category_over_time(current_user_id):
    interval = request.args.get("interval", "month")
    try:
        chart_data = budget_manager.get_transactions_by_category_over_time(current_user_id, interval)
        return jsonify({"success": True, "data": chart_data})
    except Exception as e:
        app.logger.error(f"Error in get_transactions_by_category_over_time: {e}")
        return jsonify({"success": False, "message": "伺服器內部錯誤"}), 500

@app.route("/api/reports/overspending_warnings", methods=["GET"])
@token_required
def get_overspending_warnings(current_user_id):
    month = request.args.get("month")
    try:
        warnings = budget_manager.check_over_warnings(current_user_id, month)
        return jsonify({"success": True, "data": warnings})
    except Exception as e:
        app.logger.error(f"Error in get_overspending_warnings: {e}")
        return jsonify({"success": False, "message": "伺服器內部錯誤"}), 500

@app.route("/api/reports/goal_summary", methods=["GET"])
@token_required
def get_goal_summary(current_user_id):
    try:
        summary = goal_manager.calculate_goal_summary(current_user_id)
        return jsonify({"success": True, "data": summary
    except Exception as e:
        app.logger.error(f"Error in get_goal_summary: {e}")
        return jsonify({"success": False, "message": "伺服器內部錯誤"}), 500

@app.route("/line-webhook", methods=["POST"])
def line_webhook():
    """Line Bot Webhook 端點 (已重構)"""
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    app.logger.info(f"Request body: {body}")

    try:
        # 使用 manager 中的 handler 來驗證簽名並解析事件
        events = linebot_manager.handler.parser.parse(body, signature)
    except InvalidSignatureError:
        app.logger.warning("Invalid signature. Please check your channel secret.")
        return 'Invalid signature', 400
    except Exception as e:
        app.logger.error(f"Error parsing webhook body: {e}")
        return 'Error parsing request', 400

    # 遍歷所有事件
    for event in events:
        # 目前只處理文字訊息事件
        if isinstance(event, MessageEvent) and isinstance(event.message, TextMessage):
            try:
                # 現在 handle_message_flex 會自動從 db_session 獲取 session
                linebot_manager.handle_message_flex(event)
                db_session.commit() # Add commit after successful handling
            except Exception as e:
                app.logger.error(f"Error handling Line event: {e}")
                # 如果處理過程中發生任何錯誤，回覆使用者一個通用錯誤訊息
                linebot_manager.reply_message_flex(event.reply_token, "抱歉，處理您的請求時發生內部錯誤，請稍後再試。")

    return 'OK'

@app.route("/line-login-callback", methods=["GET"])
def line_login_callback():
    code = request.args.get('code')
    if not code:
        return jsonify({"success": False, "message": "授權碼遺失"}), 400

    try:
        # 1. 交換 Token
        token_url = "https://api.line.me/oauth2/v2.1/token"
        redirect_uri = f"{VITE_BACKEND_BASE_URL}/line-login-callback"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'grant_type': 'authorization_code', 'code': code, 'redirect_uri': redirect_uri,
            'client_id': LINE_CHANNEL_ID, 'client_secret': LINE_CHANNEL_SECRET
        }
        response = requests.post(token_url, headers=headers, data=data)
        response.raise_for_status()
        id_token = response.json().get('id_token')

        # 2. 驗證 ID Token
        decoded_id_token = jwt.decode(
            id_token, LINE_CHANNEL_SECRET, algorithms=['HS256'],
            audience=LINE_CHANNEL_ID, issuer='https://access.line.me'
        )
        user_id = decoded_id_token.get('sub')
        display_name = decoded_id_token.get('name')
        if not user_id:
            raise ValueError("無法從 ID Token 獲取使用者 ID")

        # 3. 獲取或創建使用者 (使用新的 DB Session 模式)
        user = user_manager.get_or_create_user(user_id, display_name)
        db_session.commit() # Commit after user creation/retrieval

        # 4. 產生應用程式 JWT
        payload = {
            'user_id': user['user_id'],
            'name': user['display_name'],
            'exp': datetime.now(timezone.utc) + timedelta(days=1)
        }
        app_token = jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")

        # 5. 重定向到前端
        return redirect(f"{FRONTEND_BASE_URL}/auth-callback?token={app_token}")

    except requests.exceptions.RequestException as e:
        app.logger.error(f"Line Token Exchange Error: {e}")
        return jsonify({"success": False, "message": f"Line 認證失敗: {e}"}), 500
    except jwt.PyJWTError as e:
        app.logger.error(f"ID Token Verification Error: {e}")
        return jsonify({"success": False, "message": f"ID Token 驗證失敗: {e}"}), 500
    except Exception as e:
        app.logger.error(f"Unhandled Line Login Callback Error: {e}")
        return jsonify({"success": False, "message": f"登入處理失敗: {e}"}), 500
    
@app.route('/healthcheck')
def healthcheck():
    """一個簡單的健康檢查端點，只為了讓服務保持啟動"""
    return "OK", 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
