from datetime import datetime, timedelta, timezone
from functools import wraps
from uuid import UUID
from urllib.parse import urlencode
import time

from flask import Flask, jsonify, request, redirect, g
from flask_cors import CORS
from sqlalchemy import select, func
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, PostbackEvent
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
from models.schema import transactions_table, trips_table
from models.trip_manager import TripManager
from models.user_manager import UserManager

LINE_CHANNEL_ID = os.getenv("LINE_LOGIN_CHANNEL_ID")
LINE_CHANNEL_SECRET = os.getenv("LINE_LOGIN_CHANNEL_SECRET")
VITE_BACKEND_BASE_URL = os.getenv("VITE_BACKEND_BASE_URL")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")
DEV_AUTH_BYPASS = os.getenv("DEV_AUTH_BYPASS") == "true" and os.getenv("FLASK_ENV") != "production"
SLOW_REQUEST_LOG_MS = float(os.getenv("SLOW_REQUEST_LOG_MS", "500"))
DEV_AUTH_USERS = {
    "local-dev-user": {
        "display_name": "Dev User",
        "provider_email": "dev@example.local",
    },
    "amy-dev-user": {
        "display_name": "Amy",
        "provider_email": "amy@example.local",
    },
    "ben-dev-user": {
        "display_name": "Ben",
        "provider_email": "ben@example.local",
    },
    "cara-dev-user": {
        "display_name": "Cara",
        "provider_email": "cara@example.local",
    },
}
LINE_LOGIN_STATE_TTL_MINUTES = 10

if not all([LINE_CHANNEL_ID, LINE_CHANNEL_SECRET, JWT_SECRET_KEY, VITE_BACKEND_BASE_URL]):
    raise EnvironmentError("缺少必要的環境變數，請檢查 .env 檔案。 সন")

# 實例化 Flask 應用程式
app = Flask(__name__)
CORS(
    app,
    origins=[
        "https://personal-finance-gilt.vercel.app",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        FRONTEND_BASE_URL,
    ],
    supports_credentials=True
)

# 實例化 Manager
asset_manager = AssetManager(db_session)
budget_manager = BudgetManager(db_session)
goal_manager = GoalManager(db_session)
trip_manager = TripManager(db_session)
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
        if DEV_AUTH_BYPASS:
            provider_user_id = request.headers.get("X-Dev-User", "local-dev-user")
            dev_user = DEV_AUTH_USERS.get(provider_user_id, DEV_AUTH_USERS["local-dev-user"])
            user = user_manager.get_or_create_user_for_identity(
                provider="dev",
                provider_user_id=provider_user_id if provider_user_id in DEV_AUTH_USERS else "local-dev-user",
                display_name=dev_user["display_name"],
                provider_email=dev_user["provider_email"],
            )
            db_session.commit()
            return f(str(user["id"]), *args, **kwargs)

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

def _safe_frontend_redirect_path(value):
    """只允許前端站內路徑，避免登入 callback 形成 open redirect。"""
    if not value:
        return "/"
    text = str(value)
    if not text.startswith("/") or text.startswith("//"):
        return "/"
    if "\n" in text or "\r" in text:
        return "/"
    return text

def _create_line_login_state(redirect_path):
    payload = {
        "type": "line_login_state",
        "redirect": _safe_frontend_redirect_path(redirect_path),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=LINE_LOGIN_STATE_TTL_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")

def _decode_line_login_state(state):
    try:
        payload = jwt.decode(state, JWT_SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise ValueError("LINE Login state 驗證失敗") from exc
    if payload.get("type") != "line_login_state":
        raise ValueError("LINE Login state 類型不正確")
    return _safe_frontend_redirect_path(payload.get("redirect"))

app_state = AppStateManager()
linebot_manager = LineBotManager(app_state, db_session)

@app.before_request
def start_request_timer():
    g.request_started_at = time.perf_counter()


@app.after_request
def log_request_duration(response):
    started_at = getattr(g, "request_started_at", None)
    if started_at is None:
        return response

    duration_ms = (time.perf_counter() - started_at) * 1000
    response.headers["X-Request-Duration-Ms"] = f"{duration_ms:.1f}"
    if request.path.startswith("/api/") or request.path.startswith("/line-"):
        log_message = "request_timing method=%s path=%s status=%s duration_ms=%.1f"
        log_args = (request.method, request.path, response.status_code, duration_ms)
        if duration_ms >= SLOW_REQUEST_LOG_MS:
            app.logger.warning(log_message, *log_args)
        else:
            app.logger.info(log_message, *log_args)
    return response


@app.route("/")
def home():
    """根路由，回傳歡迎訊息"""
    return "歡迎來到個人財務管理系統的後端 API！"

# --- API - AI 快速輸入 ---

@app.route("/api/ai/parse", methods=["POST"])
@token_required
def parse_ai_input(current_user_id):
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or data.get("message") or "").strip()
    if not text:
        return jsonify({"success": False, "message": "缺少 text 欄位"}), 400

    try:
        parse_result = linebot_manager.message_parser.parse_shared(text)
        parse_event = linebot_manager.ai_parse_event_manager.record_from_parse_result(
            current_user_id,
            "web",
            parse_result,
        )
        db_session.commit()
        return jsonify({
            "success": True,
            "data": {
                "parse_event_id": str(parse_event["id"]),
                "parse_result": parse_result,
            },
        }), 200
    except Exception as e:
        db_session.rollback()
        app.logger.error(f"Error in parse_ai_input: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/ai/parse-events", methods=["GET"])
@token_required
def get_ai_parse_events(current_user_id):
    try:
        events = linebot_manager.ai_parse_event_manager.list_recent_events(
            current_user_id,
            limit=request.args.get("limit", 20),
        )
        return jsonify({"success": True, "data": events}), 200
    except Exception as e:
        app.logger.error(f"Error in get_ai_parse_events: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

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

@app.route("/api/dashboard/overview", methods=["GET"])
@token_required
def get_dashboard_overview(current_user_id):
    try:
        return jsonify({
            "success": True,
            "data": {
                "transactions": budget_manager.get_all_transactions(current_user_id),
                "monthly_report_transactions": budget_manager.get_all_transactions(
                    current_user_id,
                    monthly_report=True,
                ),
                "trips": trip_manager.list_trips(current_user_id),
            },
        }), 200
    except Exception as e:
        app.logger.error(f"Error in get_dashboard_overview: {e}")
        return jsonify({"success": False, "message": "伺服器內部錯誤"}), 500

@app.route("/api/assets", methods=["POST"])
@token_required
def add_asset(current_user_id):
    data = request.get_json()
    if not data or not all(k in data for k in ["bank_name", "account_type", "balance"]):
        return jsonify({"success": False, "message": "缺少必要欄位"}), 400
    
    try:
        success, message = asset_manager.add_account(
            current_user_id,
            data["bank_name"],
            data["account_type"],
            data["balance"],
            currency=data.get("currency"),
        )
        if success:
            parse_event_id = data.get("parse_event_id")
            created_transaction_id = getattr(budget_manager, "last_created_transaction_id", None)
            if parse_event_id and created_transaction_id:
                linebot_manager.ai_parse_event_manager.confirm_event(
                    current_user_id,
                    parse_event_id,
                    data["type"],
                    created_transaction_id,
                )
            db_session.commit()
        return jsonify({
            "success": success,
            "message": message,
            "data": {
                "transaction_id": str(getattr(budget_manager, "last_created_transaction_id", "")) or None,
            },
        }), 201
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

# --- API - 旅行帳本 ---

@app.route("/api/trips", methods=["GET"])
@token_required
def get_trips(current_user_id):
    include_archived = request.args.get("include_archived") == "true"
    include_deleted = request.args.get("include_deleted") == "true"
    try:
        trips = trip_manager.list_trips(
            current_user_id,
            include_archived=include_archived,
            include_deleted=include_deleted,
        )
        return jsonify({"success": True, "data": trips}), 200
    except Exception as e:
        app.logger.error(f"Error in get_trips: {e}")
        return jsonify({"success": False, "message": "伺服器內部錯誤"}), 500

@app.route("/api/trips", methods=["POST"])
@token_required
def create_trip(current_user_id):
    data = request.get_json()
    required_fields = ["name", "start_date", "end_date"]
    if not data or not all(k in data for k in required_fields):
        return jsonify({"success": False, "message": "缺少必要欄位"}), 400

    try:
        trip = trip_manager.create_trip(
            user_id=current_user_id,
            name=data["name"],
            destination=data.get("destination"),
            start_date=data["start_date"],
            end_date=data["end_date"],
            timezone_name=data.get("timezone", "Asia/Taipei"),
            base_currency=data.get("base_currency", "TWD"),
            default_currency=data.get("default_currency", data.get("base_currency", "TWD")),
            include_in_monthly_report=bool(data.get("include_in_monthly_report", False)),
        )
        db_session.commit()
        return jsonify({"success": True, "message": "旅行建立成功", "data": trip}), 201
    except Exception as e:
        app.logger.error(f"Error in create_trip: {e}")
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/trips/<string:trip_id>", methods=["GET"])
@token_required
def get_trip(current_user_id, trip_id):
    try:
        trip = trip_manager.get_trip(current_user_id, trip_id)
        return jsonify({"success": True, "data": trip}), 200
    except Exception as e:
        app.logger.error(f"Error in get_trip: {e}")
        return jsonify({"success": False, "message": str(e)}), 404

@app.route("/api/trips/<string:trip_id>/overview", methods=["GET"])
@token_required
def get_trip_overview(current_user_id, trip_id):
    try:
        overview_started_at = time.perf_counter()
        segment_timings = {}

        segment_started_at = time.perf_counter()
        trip = trip_manager.get_trip(current_user_id, trip_id)
        segment_timings["get_trip_ms"] = (time.perf_counter() - segment_started_at) * 1000
        current_member = next(
            (member for member in trip["members"] if member.get("id") == trip.get("current_member_id")),
            None,
        )

        segment_timings["invite_ms"] = 0

        segment_started_at = time.perf_counter()
        transactions = budget_manager.get_all_transactions(
            current_user_id,
            trip_id=trip_id,
            limit=request.args.get("limit", 50),
            trip=trip,
            current_trip_member=current_member,
        )
        segment_timings["transactions_ms"] = (time.perf_counter() - segment_started_at) * 1000

        segment_started_at = time.perf_counter()
        split_summary = budget_manager.get_trip_split_summary(current_user_id, trip_id, trip=trip)
        segment_timings["split_summary_ms"] = (time.perf_counter() - segment_started_at) * 1000

        segment_timings["settlement_suggestions_ms"] = 0
        segment_timings["settlements_ms"] = 0

        segment_timings["total_ms"] = (time.perf_counter() - overview_started_at) * 1000
        app.logger.warning(
            "overview_timing trip_id=%s get_trip_ms=%.1f invite_ms=%.1f transactions_ms=%.1f "
            "split_summary_ms=%.1f settlement_suggestions_ms=%.1f settlements_ms=%.1f total_ms=%.1f",
            trip_id,
            segment_timings["get_trip_ms"],
            segment_timings["invite_ms"],
            segment_timings["transactions_ms"],
            segment_timings["split_summary_ms"],
            segment_timings["settlement_suggestions_ms"],
            segment_timings["settlements_ms"],
            segment_timings["total_ms"],
        )

        return jsonify({
            "success": True,
            "data": {
                "trip": trip,
                "transactions": transactions,
                "split_summary": split_summary,
                "settlement_suggestions": [],
                "settlements": [],
                "invite": None,
            },
        }), 200
    except Exception as e:
        app.logger.error(f"Error in get_trip_overview: {e}")
        return jsonify({"success": False, "message": str(e)}), 404

@app.route("/api/trips/<string:trip_id>/members", methods=["GET"])
@token_required
def get_trip_members(current_user_id, trip_id):
    try:
        members = trip_manager.list_trip_members(current_user_id, trip_id)
        return jsonify({"success": True, "data": members}), 200
    except Exception as e:
        app.logger.error(f"Error in get_trip_members: {e}")
        return jsonify({"success": False, "message": str(e)}), 404

@app.route("/api/trips/<string:trip_id>/members", methods=["POST"])
@token_required
def add_trip_member(current_user_id, trip_id):
    data = request.get_json()
    if not data or "display_name" not in data:
        return jsonify({"success": False, "message": "缺少 display_name 欄位"}), 400

    try:
        member = trip_manager.add_external_member(
            current_user_id,
            trip_id,
            display_name=data["display_name"],
            role=data.get("role", "viewer"),
        )
        db_session.commit()
        return jsonify({"success": True, "message": "旅伴新增成功", "data": member}), 201
    except Exception as e:
        app.logger.error(f"Error in add_trip_member: {e}")
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/trips/<string:trip_id>/members/<string:member_id>", methods=["DELETE"])
@token_required
def delete_trip_member(current_user_id, trip_id, member_id):
    try:
        member = trip_manager.remove_member(current_user_id, trip_id, member_id)
        db_session.commit()
        return jsonify({"success": True, "message": "旅伴已刪除", "data": member}), 200
    except Exception as e:
        app.logger.error(f"Error in delete_trip_member: {e}")
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/trips/<string:trip_id>/members/<string:member_id>/role", methods=["PATCH"])
@token_required
def update_trip_member_role(current_user_id, trip_id, member_id):
    data = request.get_json(silent=True) or {}
    try:
        member = trip_manager.update_member_role(
            current_user_id,
            trip_id,
            member_id,
            role=data.get("role"),
        )
        db_session.commit()
        return jsonify({"success": True, "message": "旅伴權限已更新", "data": member}), 200
    except Exception as e:
        db_session.rollback()
        app.logger.error(f"Error in update_trip_member_role: {e}")
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/trips/<string:trip_id>/leave", methods=["POST"])
@token_required
def leave_trip(current_user_id, trip_id):
    try:
        member = trip_manager.leave_trip(current_user_id, trip_id)
        db_session.commit()
        return jsonify({"success": True, "message": "已退出旅行帳本", "data": member}), 200
    except Exception as e:
        db_session.rollback()
        app.logger.error(f"Error in leave_trip: {e}")
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/trips/<string:trip_id>/invite", methods=["GET"])
@token_required
def get_trip_invite(current_user_id, trip_id):
    try:
        invite = trip_manager.get_active_invite(current_user_id, trip_id)
        return jsonify({"success": True, "data": invite}), 200
    except Exception as e:
        app.logger.error(f"Error in get_trip_invite: {e}")
        return jsonify({"success": False, "message": str(e)}), 404

@app.route("/api/trips/<string:trip_id>/invite", methods=["POST"])
@token_required
def create_trip_invite(current_user_id, trip_id):
    data = request.get_json(silent=True) or {}
    try:
        invite = trip_manager.create_invite(
            current_user_id,
            trip_id,
            role=data.get("role", "editor"),
            expires_in_days=int(data.get("expires_in_days", 30)),
        )
        invite["invite_url"] = f"{FRONTEND_BASE_URL.rstrip('/')}/trips/invite/{invite['token']}"
        db_session.commit()
        return jsonify({"success": True, "message": "邀請連結已建立", "data": invite}), 201
    except Exception as e:
        db_session.rollback()
        app.logger.error(f"Error in create_trip_invite: {e}")
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/trips/<string:trip_id>/invite", methods=["DELETE"])
@token_required
def close_trip_invite(current_user_id, trip_id):
    try:
        invite = trip_manager.close_invite(current_user_id, trip_id)
        db_session.commit()
        return jsonify({"success": True, "message": "邀請連結已關閉", "data": invite}), 200
    except Exception as e:
        db_session.rollback()
        app.logger.error(f"Error in close_trip_invite: {e}")
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/trip-invites/<string:token>/accept", methods=["POST"])
@token_required
def accept_trip_invite(current_user_id, token):
    try:
        result = trip_manager.accept_invite(current_user_id, token)
        db_session.commit()
        return jsonify({"success": True, "message": "已加入旅行帳本", "data": result}), 200
    except Exception as e:
        db_session.rollback()
        app.logger.error(f"Error in accept_trip_invite: {e}")
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/trips/<string:trip_id>/split-summary", methods=["GET"])
@token_required
def get_trip_split_summary(current_user_id, trip_id):
    try:
        summary = budget_manager.get_trip_split_summary(current_user_id, trip_id)
        return jsonify({"success": True, "data": summary}), 200
    except Exception as e:
        app.logger.error(f"Error in get_trip_split_summary: {e}")
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/trips/<string:trip_id>/split-state", methods=["GET"])
@token_required
def get_trip_split_state(current_user_id, trip_id):
    try:
        split_summary = budget_manager.get_trip_split_summary(current_user_id, trip_id)
        settlement_suggestions = budget_manager.get_trip_settlement_suggestions(
            current_user_id,
            trip_id,
            summary=split_summary,
        )
        settlements = budget_manager.get_trip_settlements(current_user_id, trip_id)
        return jsonify({
            "success": True,
            "data": {
                "split_summary": split_summary,
                "settlement_suggestions": settlement_suggestions,
                "settlements": settlements,
            },
        }), 200
    except Exception as e:
        app.logger.error(f"Error in get_trip_split_state: {e}")
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/trips/<string:trip_id>/settlement-suggestions", methods=["GET"])
@token_required
def get_trip_settlement_suggestions(current_user_id, trip_id):
    try:
        suggestions = budget_manager.get_trip_settlement_suggestions(current_user_id, trip_id)
        return jsonify({"success": True, "data": suggestions}), 200
    except Exception as e:
        app.logger.error(f"Error in get_trip_settlement_suggestions: {e}")
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/trips/<string:trip_id>/settlements", methods=["GET"])
@token_required
def get_trip_settlements(current_user_id, trip_id):
    try:
        settlements = budget_manager.get_trip_settlements(current_user_id, trip_id)
        return jsonify({"success": True, "data": settlements}), 200
    except Exception as e:
        app.logger.error(f"Error in get_trip_settlements: {e}")
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/trips/<string:trip_id>/settlements", methods=["POST"])
@token_required
def add_trip_settlement(current_user_id, trip_id):
    data = request.get_json()
    required_fields = ["from_member_id", "to_member_id", "amount"]
    if not data or not all(k in data for k in required_fields):
        return jsonify({"success": False, "message": "缺少必要欄位"}), 400

    try:
        success, message = budget_manager.add_trip_settlement(
            current_user_id,
            trip_id,
            data["from_member_id"],
            data["to_member_id"],
            data["amount"],
            note=data.get("note"),
        )
        if success:
            created_transaction_id = getattr(budget_manager, "last_created_transaction_id", None)
            parse_event_id = data.get("parse_event_id")
            if parse_event_id and created_transaction_id:
                linebot_manager.ai_parse_event_manager.confirm_event(
                    current_user_id,
                    parse_event_id,
                    data["type"],
                    created_transaction_id,
                )
            db_session.commit()
        return jsonify({
            "success": success,
            "message": message,
            "data": {
                "transaction_id": str(getattr(budget_manager, "last_created_transaction_id", "")) or None,
            },
        }), 201
    except Exception as e:
        db_session.rollback()
        app.logger.error(f"Error in add_trip_settlement: {e}")
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/trips/<string:trip_id>/settlements/<string:settlement_id>", methods=["DELETE"])
@token_required
def delete_trip_settlement(current_user_id, trip_id, settlement_id):
    try:
        success, message = budget_manager.delete_trip_settlement(current_user_id, trip_id, settlement_id)
        if success:
            db_session.commit()
        return jsonify({"success": success, "message": message}), 200
    except Exception as e:
        db_session.rollback()
        app.logger.error(f"Error in delete_trip_settlement: {e}")
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/trips/<string:trip_id>/archive", methods=["POST"])
@token_required
def archive_trip(current_user_id, trip_id):
    try:
        trip = trip_manager.archive_trip(current_user_id, trip_id)
        db_session.commit()
        return jsonify({"success": True, "message": "旅行已封存", "data": trip}), 200
    except Exception as e:
        app.logger.error(f"Error in archive_trip: {e}")
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/trips/<string:trip_id>/unarchive", methods=["POST"])
@token_required
def unarchive_trip(current_user_id, trip_id):
    try:
        trip = trip_manager.unarchive_trip(current_user_id, trip_id)
        db_session.commit()
        return jsonify({"success": True, "message": "旅行已解除封存", "data": trip}), 200
    except Exception as e:
        app.logger.error(f"Error in unarchive_trip: {e}")
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/trips/<string:trip_id>/restore", methods=["POST"])
@token_required
def restore_trip(current_user_id, trip_id):
    try:
        trip = trip_manager.restore_trip(current_user_id, trip_id)
        db_session.commit()
        return jsonify({"success": True, "message": "旅行已復原", "data": trip}), 200
    except Exception as e:
        app.logger.error(f"Error in restore_trip: {e}")
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/trips/<string:trip_id>", methods=["DELETE"])
@token_required
def delete_trip(current_user_id, trip_id):
    try:
        trip = trip_manager.delete_trip(current_user_id, trip_id)
        db_session.commit()
        return jsonify({"success": True, "message": "旅行已刪除", "data": trip}), 200
    except Exception as e:
        app.logger.error(f"Error in delete_trip: {e}")
        return jsonify({"success": False, "message": str(e)}), 400

# --- API - 預算與支出管理 ---

@app.route("/api/budgets/categories", methods=["GET"])
@token_required
def get_budget_categories(current_user_id):
    try:
        include_meta = request.args.get("include_meta") == "true"
        categories = budget_manager.get_all_budget_categories(current_user_id, include_meta=include_meta)
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
        created_transaction_id = getattr(budget_manager, "last_created_transaction_id", None)
        if success:
            parse_event_id = data.get("parse_event_id")
            if parse_event_id and created_transaction_id:
                linebot_manager.ai_parse_event_manager.confirm_event(
                    current_user_id,
                    parse_event_id,
                    data["type"],
                    created_transaction_id,
                )
            db_session.commit()
        return jsonify({
            "success": success,
            "message": message,
            "data": {
                "transaction_id": str(created_transaction_id) if created_transaction_id else None,
            },
        }), 201
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
        transactions_data = budget_manager.get_all_transactions(
            current_user_id,
            trip_id=request.args.get("trip_id"),
            include_trips=request.args.get("include_trips") == "true",
            monthly_report=request.args.get("monthly_report") == "true",
            limit=request.args.get("limit"),
        )
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
            data["type"], data["budget_category"], data.get("description", ""),
            account_id=data.get("account_id"),
            trip_id=data.get("trip_id"),
            paid_by_member_id=data.get("paid_by_member_id"),
            merchant=data.get("merchant"),
            original_currency=data.get("original_currency"),
            exchange_rate=data.get("exchange_rate"),
            timezone_name=data.get("timezone", "Asia/Taipei"),
            split_member_ids=data.get("split_member_ids"),
            split_allocations=data.get("split_allocations"),
            review_status=data.get("review_status", "confirmed"),
        )
        created_transaction_id = getattr(budget_manager, "last_created_transaction_id", None)
        if success:
            parse_event_id = data.get("parse_event_id")
            if parse_event_id and created_transaction_id:
                linebot_manager.ai_parse_event_manager.confirm_event(
                    current_user_id,
                    parse_event_id,
                    data["type"],
                    created_transaction_id,
                )
            db_session.commit()
        return jsonify({
            "success": success,
            "message": message,
            "data": {
                "transaction_id": str(created_transaction_id) if created_transaction_id else None,
            },
        }), 201
    except Exception as e:
        db_session.rollback()
        app.logger.error(f"Error in add_transaction: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/transactions/<string:transaction_id>", methods=["GET"])
@token_required
def get_transaction_detail(current_user_id, transaction_id):
    try:
        transaction = budget_manager.get_transaction_detail(current_user_id, transaction_id)
        return jsonify({"success": True, "data": transaction}), 200
    except Exception as e:
        app.logger.error(f"Error in get_transaction_detail: {e}")
        return jsonify({"success": False, "message": str(e)}), 404

@app.route("/api/transactions/<string:transaction_id>", methods=["PUT"])
@token_required
def update_transaction(current_user_id, transaction_id):
    data = request.get_json()
    required_fields = ["date", "item", "amount", "type", "budget_category"]
    if not data or not all(k in data for k in required_fields):
        return jsonify({"success": False, "message": "缺少必要欄位"}), 400

    try:
        success, message = budget_manager.update_transaction(
            current_user_id,
            transaction_id,
            data["date"],
            data["item"],
            data["amount"],
            data["type"],
            data["budget_category"],
            data.get("description", ""),
            account_id=data.get("account_id"),
            paid_by_member_id=data.get("paid_by_member_id"),
            merchant=data.get("merchant"),
            original_currency=data.get("original_currency"),
            exchange_rate=data.get("exchange_rate"),
            timezone_name=data.get("timezone", "Asia/Taipei"),
            split_member_ids=data.get("split_member_ids"),
            split_allocations=data.get("split_allocations"),
            review_status=data.get("review_status", "confirmed"),
        )
        if success:
            db_session.commit()
        return jsonify({"success": success, "message": message}), 200
    except Exception as e:
        db_session.rollback()
        app.logger.error(f"Error in update_transaction: {e}")
        return jsonify({"success": False, "message": str(e)}), 400

@app.route("/api/transactions/<string:transaction_id>", methods=["DELETE"])
@token_required
def delete_transaction(current_user_id, transaction_id):
    try:
        success, message = budget_manager.delete_transaction(current_user_id, transaction_id)
        if success:
            db_session.commit()
        return jsonify({"success": success, "message": message}), 200
    except Exception as e:
        db_session.rollback()
        app.logger.error(f"Error in delete_transaction: {e}")
        return jsonify({"success": False, "message": str(e)}), 404

@app.route("/api/budgets/summary/<string:month>", methods=["GET"])
@token_required
def get_monthly_summary(current_user_id, month):
    try:
        response_data = budget_manager.get_budget_summary(current_user_id, month)
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
        expense_data = budget_manager.calculate_monthly_report_expenses(current_user_id, year_month)
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
        parsed_user_id = UUID(str(current_user_id))
        stmt = select(transactions_table.c.type, func.sum(transactions_table.c.converted_amount).label("total")) \
            .outerjoin(trips_table, transactions_table.c.trip_id == trips_table.c.id) \
            .where(
                transactions_table.c.user_id == parsed_user_id,
                transactions_table.c.deleted_at.is_(None),
                (
                    transactions_table.c.trip_id.is_(None)
                    | trips_table.c.include_in_monthly_report.is_(True)
                ),
            )
        if month:
            stmt = stmt.where(func.to_char(transactions_table.c.transaction_date, 'YYYY-MM') == month)
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
        return jsonify({"success": True, "data": summary})
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
        try:
            # 處理文字訊息事件
            if isinstance(event, MessageEvent) and isinstance(event.message, TextMessage):
                linebot_manager.handle_message_flex(event)
                db_session.commit()
            # 處理 Postback 事件 (例如 DatetimePicker)
            elif isinstance(event, PostbackEvent):
                linebot_manager.handle_postback_event(event)
                db_session.commit()
        except Exception as e:
            app.logger.error(f"Error handling Line event: {e}")
            # 如果處理過程中發生任何錯誤，回覆使用者一個通用錯誤訊息
            linebot_manager.reply_message_flex(event.reply_token, "抱歉，處理您的請求時發生內部錯誤，請稍後再試。")

    return 'OK'

@app.route("/line-login-start", methods=["GET"])
def line_login_start():
    redirect_path = _safe_frontend_redirect_path(request.args.get("redirect", "/"))
    redirect_uri = f"{VITE_BACKEND_BASE_URL}/line-login-callback"
    state = _create_line_login_state(redirect_path)
    query = urlencode(
        {
            "response_type": "code",
            "client_id": LINE_CHANNEL_ID,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": "profile openid",
        }
    )
    return redirect(f"https://access.line.me/oauth2/v2.1/authorize?{query}")

@app.route("/line-login-callback", methods=["GET"])
def line_login_callback():
    code = request.args.get('code')
    state = request.args.get("state")
    if not code:
        return jsonify({"success": False, "message": "授權碼遺失"}), 400
    if not state:
        return jsonify({"success": False, "message": "LINE Login state 遺失"}), 400

    try:
        frontend_redirect_path = _decode_line_login_state(state)

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
        line_user_id = decoded_id_token.get('sub')
        display_name = decoded_id_token.get('name')
        provider_email = decoded_id_token.get('email')
        avatar_url = decoded_id_token.get('picture')
        if not line_user_id:
            raise ValueError("無法從 ID Token 獲取使用者 ID")

        # 3. 獲取或創建內部使用者，LINE ID 會存到 user_identities
        user = user_manager.get_or_create_user_for_identity(
            provider="line",
            provider_user_id=line_user_id,
            display_name=display_name,
            provider_email=provider_email,
            avatar_url=avatar_url,
        )
        db_session.commit() # Commit after user creation/retrieval

        # 4. 產生應用程式 JWT
        payload = {
            'user_id': str(user['id']),
            'line_user_id': line_user_id,
            'name': user['display_name'],
            'exp': datetime.now(timezone.utc) + timedelta(days=1)
        }
        app_token = jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")

        # 5. 重定向到前端
        callback_query = urlencode({"token": app_token, "redirect": frontend_redirect_path})
        return redirect(f"{FRONTEND_BASE_URL}/auth-callback?{callback_query}")

    except requests.exceptions.RequestException as e:
        app.logger.error(f"Line Token Exchange Error: {e}")
        return jsonify({"success": False, "message": f"Line 認證失敗: {e}"}), 500
    except jwt.PyJWTError as e:
        app.logger.error(f"ID Token Verification Error: {e}")
        return jsonify({"success": False, "message": f"ID Token 驗證失敗: {e}"}), 500
    except ValueError as e:
        app.logger.error(f"Line Login State Error: {e}")
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Unhandled Line Login Callback Error: {e}")
        return jsonify({"success": False, "message": f"登入處理失敗: {e}"}), 500
    
@app.route('/healthcheck')
def healthcheck():
    """一個簡單的健康檢查端點，只為了讓服務保持啟動"""
    return "OK", 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
