# models/linebot/manager.py

import os
import google.generativeai as genai
from .message_handler import MessageHandler
from .message_parser import MessageParser
from .user_state_manager import UserStateManager
from ..user_manager import UserManager
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import LineBotApiError
from linebot.models import TextSendMessage

class LineBotManager:
    """
    管理 Line Bot 的核心邏輯，包含訊息的接收、解析與回覆。
    現在的設計是作為一個較無狀態的服務，由 web_app 傳入 db_session 來處理請求。
    """
    def __init__(self, app_state, db_session):
        self.app_state = app_state
        self.db_session = db_session
        # Line Bot 設定
        self.line_bot_api = LineBotApi(os.getenv("LINE_MSG_CHANNEL_ACCESS_TOKEN"))
        self.handler = WebhookHandler(os.getenv("LINE_MSG_CHANNEL_SECRET"))
        
        # Gemini 設定
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        # 建議使用較新的模型以獲得更好的解析效果
        self.model = genai.GenerativeModel('gemini-2.5-flash')

        self.user_state_manager = UserStateManager()
        self.user_manager = UserManager(self.db_session)
        
        # Prompt 模板 (保持不變)
        self.prompt_template = '''
        分析以下中文記帳訊息，並嚴格回傳 JSON 格式。

        訊息："{message}"

        **輸出欄位定義:**
        - `budget_category`: 最高層級的分類，必須是「類別限制」中的一個。
        - `category`: 次級消費類型，例如「午餐」、「晚餐」、「飲料」、「零食」、「計程車」。
        - `description`: 訊息中提到的具體「品牌」、「店家」或「品項」，例如「麥當勞」、「可口可樂」。如果沒有，此欄位為 null。
        - `amount`: 金額 (數字)。
        - `target_asset`: 支付的資產/帳戶，例如「現金」、「信用卡」、「銀行轉帳」。如果訊息中沒有提到，此欄位為 null。

        **規則：**
        1. **支出記錄**: 必須包含 `type`, `budget_category`, `category`, `amount`。
           - JSON: {{ "type": "expense", "budget_category": "...", "category": "...", "description": "...", "amount": ..., "target_asset": "..." }}
        2. **收入記錄**: 
           - JSON: {{ "type": "income", "budget_category": "收入", "category": "收入來源", "description": "備註", "amount": ..., "target_asset": "..." }}
        3. **欄位提取邏輯**: 
           - `budget_category`: 將消費目的歸類到「類別限制」中的一個。
           - `category`: 從訊息中提取次級消費類型。
           - `description`: 從訊息中提取最詳細的品項或地點。若 `category` 和 `description` 相似，優先將具體名詞填入 `description`。
           - `target_asset`: 從訊息中提取支付方式，如「用現金」、「刷卡」、「從郵局轉帳」。
        4. **其他請求**: 根據訊息類型回傳對應的 JSON 結構。

        **類別限制 (用於 budget_category):**
        伙食、交通、購物、娛樂、醫療、投資、生活、其他、收入

        **精選範例:**
        - 訊息: "午餐吃麥當勞 150元 用國泰信用卡"
          應解析為: {{ "type": "expense", "budget_category": "伙食", "category": "午餐", "description": "麥當勞", "amount": 150, "target_asset": "國泰信用卡" }}
        - 訊息: "在7-11買了可口可樂，付了現金30元"
          應解析為: {{ "type": "expense", "budget_category": "伙食", "category": "飲料", "description": "可口可樂", "amount": 30, "target_asset": "現金" }}
        - 訊息: "搭計程車回家花了 250"
          應解析為: {{ "type": "expense", "budget_category": "交通", "category": "計程車", "description": null, "amount": 250, "target_asset": null }}
        - 訊息: "治裝費 3000"
          應解析為: {{ "type": "expense", "budget_category": "購物", "category": "衣服", "description": null, "amount": 3000, "target_asset": null }}


        注意：只回傳純 JSON，不要 markdown 標記。
        '''

        self.message_parser = MessageParser(
            gemini_model=self.model,
            prompt_template=self.prompt_template,
        )
        
        self.message_handler = MessageHandler(self.user_state_manager, self.db_session)

    def handle_message_flex(self, event):
        """
        處理單一訊息事件的核心邏輯。
        由 web_app 傳入 event 和 db_session。
        """
        user_message = event.message.text.strip()
        user_id = event.source.user_id
        print(f"Received message from user_id: {user_id}")

        # 獲取使用者 Line 顯示名稱
        profile = self.line_bot_api.get_profile(user_id)
        display_name = profile.display_name

        # 確保使用者存在於資料庫中
        self.user_manager.get_or_create_user(user_id, display_name)

        if self.app_state and self.app_state.is_cold_start():
            print(f"冷啟動期間收到訊息: {user_message}")
            self.reply_message_flex(event.reply_token, "🚀 系統剛啟動完成！\n請重新發送您的訊息，我現在準備好了 😊")
            return

        # 正常的訊息解析流程
        parsed_data = self.message_parser.parse(user_message)
        
        response_message = self.message_handler.handle_user_message(user_id, user_message, parsed_data)

        self.reply_message_flex(event.reply_token, response_message)
    def reply_message_flex(self, reply_token, message):
        """
        支援 Flex Message 的回覆方法
        """
        try:
            if isinstance(message, str):
                self.line_bot_api.reply_message(reply_token, TextSendMessage(text=message))
            else:
                self.line_bot_api.reply_message(reply_token, message)
        except LineBotApiError as e:
            print(f"Line API Error: {e}")

    def push_message_flex(self, user_id, message):
        """
        支援 Flex Message 的推送方法
        """
        try:
            if isinstance(message, str):
                self.line_bot_api.push_message(user_id, TextSendMessage(text=message))
            else:
                self.line_bot_api.push_message(user_id, message)
        except LineBotApiError as e:
            print(f"Line Push Error: {e}")