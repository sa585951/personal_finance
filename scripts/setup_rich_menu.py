import os
import sys
import json
import requests
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_MSG_CHANNEL_ACCESS_TOKEN")

if not LINE_CHANNEL_ACCESS_TOKEN:
    print("Error: LINE_MSG_CHANNEL_ACCESS_TOKEN not found in .env")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

def create_rich_menu():
    rich_menu_object = {
        "size": {
            "width": 2500,
            "height": 1686
        },
        "selected": True,
        "name": "Personal Finance Menu",
        "chatBarText": "開啟選單",
        "areas": [
            {
                "bounds": {"x": 0, "y": 0, "width": 833, "height": 843},
                "action": {"type": "message", "label": "快速記帳", "text": "快速記帳"}
            },
            {
                "bounds": {"x": 833, "y": 0, "width": 834, "height": 843},
                "action": {"type": "message", "label": "資產總覽", "text": "我的資產"}
            },
            {
                "bounds": {"x": 1667, "y": 0, "width": 833, "height": 843},
                "action": {"type": "message", "label": "本月支出", "text": "查詢本月支出"}
            },
            {
                "bounds": {"x": 0, "y": 843, "width": 833, "height": 843},
                "action": {"type": "message", "label": "設定預算", "text": "設定預算"}
            },
            {
                "bounds": {"x": 833, "y": 843, "width": 834, "height": 843},
                "action": {"type": "message", "label": "財務目標", "text": "我的財務目標"}
            },
            {
                "bounds": {"x": 1667, "y": 843, "width": 833, "height": 843},
                "action": {"type": "message", "label": "更多功能", "text": "幫助"}
            }
        ]
    }

    response = requests.post(
        "https://api.line.me/v2/bot/richmenu",
        headers=HEADERS,
        data=json.dumps(rich_menu_object)
    )

    if response.status_code == 200:
        rich_menu_id = response.json()["richMenuId"]
        print(f"Rich Menu created successfully. ID: {rich_menu_id}")
        return rich_menu_id
    else:
        print(f"Failed to create Rich Menu: {response.text}")
        return None

def set_default_rich_menu(rich_menu_id):
    response = requests.post(
        f"https://api.line.me/v2/bot/user/all/richmenu/{rich_menu_id}",
        headers=HEADERS
    )

    if response.status_code == 200:
        print("Rich Menu set as default successfully.")
    else:
        print(f"Failed to set default Rich Menu: {response.text}")

def upload_rich_menu_image(rich_menu_id, image_path):
    if not os.path.exists(image_path):
        print(f"Image file not found: {image_path}")
        return

    with open(image_path, 'rb') as f:
        headers = {
            "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
            "Content-Type": "image/jpeg"
        }
        response = requests.post(
            f"https://api-data.line.me/v2/bot/richmenu/{rich_menu_id}/content",
            headers=headers,
            data=f
        )

    if response.status_code == 200:
        print("Rich Menu image uploaded successfully.")
    else:
        print(f"Failed to upload image: {response.text}")

if __name__ == "__main__":
    # 注意：你需要一張名為 'rich_menu.jpg' 的圖片 (2500x1686) 放在同一個目錄下
    # 或者你可以註解掉上傳圖片的部分，如果你只想測試版面配置
    
    print("正在建立圖文選單...")
    menu_id = create_rich_menu()
    
    if menu_id:
        # 如果你有圖片，請取消註解以下幾行
        # print("正在上傳圖片...")
        # upload_rich_menu_image(menu_id, "rich_menu.jpg")
        
        print("正在設為預設選單...")
        set_default_rich_menu(menu_id)
        
        print("完成！")
