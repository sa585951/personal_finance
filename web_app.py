import os
from flask import Flask, jsonify, request

# 為了確保匯入正確，我們需要將專案根目錄加入到路徑
# 這樣 Flask 才能找到我們的 models 和 reports
import sys
# 假設 web_app.py 位於 personal_finance 資料夾內
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 匯入我們之前建立的核心類別
from models.asset_manager import AssetManager
from models.budget_manager import BudgetManager
from models.goal_manager import GoalManager

# 實例化 Flask 應用程式
app = Flask(__name__)

# 實例化 Manager 類別，它們將在整個應用程式中被重複使用
asset_manager = AssetManager()
budget_manager = BudgetManager()
goal_manager = GoalManager()

@app.route("/")
def home():
    """根路由，回傳歡迎訊息"""
    return "歡迎來到個人財務管理系統的後端 API！"

# API - 資產管理

@app.route("/api/assets", methods=["POST"])
def add_account():
    """
    新增帳戶
    - 接收 JSON 格式的資料
    """
    data = request.get_json()
    bank_name = data.get("bank_name")
    account_type = data.get("account_type")
    balance = data.get("balance")

    if not all([bank_name, account_type, balance is not None]):
        return jsonify({"success": False, "message": "缺少必要欄位"}), 400

    success = asset_manager.add_account(bank_name, account_type, balance)
    if success:
        return jsonify({"success": True, "message": "帳戶新增成功"}), 201
    else:
        return jsonify({"success": False, "message": "帳戶新增失敗"}), 500

@app.route("/api/assets", methods=["GET"])
def get_all_assets():
    """
    獲取所有資產帳戶資料
    """
    return jsonify({"success": True, "data": asset_manager.assets})

@app.route("/api/assets/<bank_name>/<account_type>", methods=["PUT"])
def update_balance(bank_name, account_type):
    """
    更新帳戶餘額
    - 透過 URL 傳入銀行名稱與帳戶類型
    - 接收 JSON 格式的資料
    """
    data = request.get_json()
    new_balance = data.get("new_balance")

    if new_balance is None:
        return jsonify({"success": False, "message": "缺少 new_balance 欄位"}), 400

    success = asset_manager.update_balance(bank_name, account_type, new_balance)
    if success:
        return jsonify({"success": True, "message": "餘額更新成功"}), 200
    else:
        return jsonify({"success": False, "message": "更新失敗，找不到帳戶"}), 404

@app.route("/api/assets/<bank_name>/<account_type>", methods=["DELETE"])
def delete_account(bank_name, account_type):
    """
    刪除帳戶
    - 透過 URL 傳入銀行名稱與帳戶類型
    """    
    success = asset_manager.delete_account(bank_name, account_type)
    if success:
        return jsonify({"success": True, "message": "帳戶刪除成功"}), 200
    else:
        return jsonify({"success": False, "message": "刪除失敗，找不到帳戶"}), 404

# API - 預算與支出管理

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

@app.route("/api/budgets/delete", methods=["DELETE"])
def delete_budget():
    """
    刪除某月某類別的預算
    - 接收 JSON 格式的資料
    """
    data = request.get_json()
    month = data.get("month")
    category = data.get("category")

    if not all([month, category]):
        return jsonify({"success": False, "message": "缺少必要欄位"}), 400

    success = budget_manager.delete_budget(month, category)
    if success:
        return jsonify({"success": True, "message": "預算刪除成功"}), 200
    else:
        return jsonify({"success": False, "message": "預算刪除失敗，找不到預算"}), 404

@app.route("/api/transactions", methods=["GET", "POST"])
def manage_transactions():
    """
    管理所有交易紀錄（新增與獲取）
    - GET: 獲取所有交易
    - POST: 新增一筆交易
    """
    if request.method == "POST":
        data = request.get_json()
        required_fields = ["date", "type", "category", "amount"]
        if not all(field in data for field in required_fields):
            return jsonify({"success": False, "message": "缺少必要欄位"}), 400

        # 將數據傳給 BudgetManager
        success = budget_manager.add_transaction(
            data["date"],
            data["type"],
            data["category"],
            data["amount"],
        )
        if success:
            return jsonify({"success": True, "message": "交易記錄成功"}), 201
        else:
            return jsonify({"success": False, "message": "交易記錄失敗"}), 500
    
    elif request.method == "GET":
        transactions_data = budget_manager.get_all_transactions()
        if transactions_data:
            return jsonify({"success": True, "data": transactions_data}), 200
        else:
            return jsonify({"success": False, "message": "沒有找到交易紀錄"}), 404

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
    expense_totals = budget_manager.calculate_monthly_expenses(month)
    
    if not expense_totals:
        return jsonify({"success": False, "message": "該月沒有支出記錄"}), 404
    
    budgets = budget_manager.budgets.get(month, {})
    response_data = []

    for category, spent_amount in expense_totals.items():
        budget_info = budgets.get(category)
        item = {
            "category": category,
            "spent": spent_amount,
            "budget": budget_info.get("amount") if budget_info else None,
            "remaining": (budget_info.get("amount", 0) - spent_amount) if budget_info else None
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
def update_goal_progress(goal_id):
    """
    更新目標進度
    - 透過 URL 傳入目標 ID
    - 接收 JSON 格式的資料
    """
    data = request.get_json()
    new_current_amount = data.get("new_current_amount")

    if new_current_amount is None:
        return jsonify({"success": False, "message": "缺少 new_current_amount 欄位"}), 400
    
    success = goal_manager.update_goal_progress(goal_id, new_current_amount)
    if success:
        return jsonify({"success": True, "message": "目標進度更新成功"}), 200
    else:
        return jsonify({"success": False, "message": "目標進度更新失敗，找不到目標"}), 404

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

if __name__ == '__main__':
    # 執行 Flask 應用程式
    app.run(debug=True)