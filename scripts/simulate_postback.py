import os
import sys
import json
import hmac
import hashlib
import base64
import requests
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 設定
CHANNEL_SECRET = os.getenv("LINE_MSG_CHANNEL_SECRET")
WEBHOOK_URL = "http://localhost:5000/line-webhook"

if not CHANNEL_SECRET:
    print("Error: LINE_MSG_CHANNEL_SECRET not found in .env")
    sys.exit(1)

def generate_signature(body, secret):
    """產生 X-Line-Signature 標頭。"""
    hash = hmac.new(
        secret.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    ).digest()
    return base64.b64encode(hash).decode('utf-8')

def send_event(event_type, text=None, reply_token="dummy_token", user_id="U1234567890abcdef1234567890abcdef"):
    """發送模擬的 Line 事件。"""
    
    # 建構事件負載
    event = {
        "type": event_type,
        "replyToken": reply_token,
        "source": {
            "userId": user_id,
            "type": "user"
        },
        "timestamp": 1625666000000,
        "mode": "active"
    }

    if event_type == "message":
        event["message"] = {
            "type": "text",
            "id": "14353798921116",
            "text": text
        }
    elif event_type == "postback":
        # text 這裡當作 postback data
        # 如果 text 包含 params (例如 "action=select_month&date=2025-10-01")，需要解析
        data = text
        params = {}
        if "&" in text:
            parts = text.split("&")
            data = parts[0] # 假設第一個是 data
            for part in parts[1:]:
                if "=" in part:
                    k, v = part.split("=")
                    if k in ['date', 'time', 'datetime']:
                        params[k] = v
        
        event["postback"] = {
            "data": data,
            "params": params
        }
    
    payload = {
        "destination": "U1234567890abcdef1234567890abcdef",
        "events": [event]
    }
    
    body = json.dumps(payload)
    signature = generate_signature(body, CHANNEL_SECRET)
    
    headers = {
        "Content-Type": "application/json",
        "X-Line-Signature": signature
    }
    
    print(f"Sending {event_type}: {text}")
    try:
        response = requests.post(WEBHOOK_URL, headers=headers, data=body)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to localhost:5000. Is the server running?")
        return False

def run_test_scenario():
    print("=== 開始模擬測試 (Postback) ===")
    
    # 1. 測試 "設定預算" 觸發
    print("\n[測試 1] 觸發設定預算流程")
    if not send_event("message", "設定預算"): return

    # 2. 測試 "選擇月份" (模擬 Postback: action=select_month&date=2025-10-01)
    print("\n[測試 2] 選擇月份 (Postback)")
    if not send_event("postback", "action=select_month&date=2025-10-01"): return

    # 3. 測試 "選擇類別" (模擬使用者回覆 "伙食")
    print("\n[測試 3] 選擇類別")
    if not send_event("message", "伙食"): return

    # 4. 測試 "輸入金額" (模擬使用者回覆 "5000")
    print("\n[測試 4] 輸入金額")
    if not send_event("message", "5000"): return
    
    print("\n=== 測試完成 ===")

    print("\n=== 開始模擬測試 (取消流程) ===")
    # 1. 觸發設定預算
    print("\n[測試 5] 觸發設定預算 (準備取消)")
    send_event("message", "設定預算")
    
    # 2. 發送取消指令
    print("\n[測試 6] 發送取消指令")
    send_event("message", "取消")
    
    print("\n=== 取消測試完成 ===")

if __name__ == "__main__":
    run_test_scenario()
