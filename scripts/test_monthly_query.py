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

def send_event(text):
    """發送模擬的 Line 文字訊息事件。"""
    event = {
        "type": "message",
        "replyToken": "test_token",
        "source": {"userId": "U1234567890abcdef1234567890abcdef", "type": "user"},
        "timestamp": 1625666000000,
        "mode": "active",
        "message": {"type": "text", "id": "14353798921116", "text": text}
    }
    
    payload = {"destination": "U1234567890abcdef1234567890abcdef", "events": [event]}
    body = json.dumps(payload)
    signature = generate_signature(body, CHANNEL_SECRET)
    headers = {"Content-Type": "application/json", "X-Line-Signature": signature}
    
    print(f"Sending: {text}")
    try:
        response = requests.post(WEBHOOK_URL, headers=headers, data=body)
        print(f"Status: {response.status_code}, Response: {response.text}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to localhost:5000")
        return False

if __name__ == "__main__":
    print("=== 測試查詢本月支出 ===")
    send_event("查詢本月支出")
    print("\n=== 測試完成 ===")
