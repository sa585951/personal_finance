import os
import google.generativeai as genai
from datetime import datetime
from .message_handler import MessageHandler
from .message_parser import MessageParser
from .user_state_manager import UserStateManager
from ..user_manager import UserManager # Import UserManager
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, 
    FlexSendMessage
)

class LineBotManager:
    def __init__(self, budget_manager, asset_manager, goal_manager, app_state, user_manager):

        self.app_state = app_state
        #Line Bot設定
        self.line_bot_api = LineBotApi(os.getenv("LINE_MSG_CHANNEL_ACCESS_TOKEN"))
        self.handler = WebhookHandler(os.getenv("LINE_MSG_CHANNEL_SECRET"))
        
        # Gemini設定
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-2.5-flash')

        #依賴注入現有 managers
        self.user_state_manager = UserStateManager()
        self.user_manager = user_manager # Assign the passed user_manager
        # Prompt模板
        self.prompt_template = """
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
           - JSON: {{"type": "expense", "budget_category": "...", "category": "...", "description": "...", "amount": ..., "target_asset": "..."}}
        2. **收入記錄**:
           - JSON: {{"type": "income", "budget_category": "收入", "category": "收入來源", "description": "備註", "amount": ..., "target_asset": "..."}}
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
        """

        #注入Message Parser
        self.message_parser = MessageParser(
            gemini_model=self.model,
            prompt_template=self.prompt_template,
        )

        # 建立 Handler實例
        self.message_handler = MessageHandler(budget_manager, asset_manager, goal_manager, self.user_state_manager)
        # 註冊事件處理器
        self.register_handlers()

    def register_handlers(self):
        """註冊 Line Bot 事件處理器"""
        @self.handler.add(MessageEvent, message=TextMessage)
        def handle_text_message(event):
            self.handle_message_flex(event)

    def handle_message_flex(self, event):
        """支援 Flex Message 的訊息處理 - 加入冷啟動檢測"""
        user_message = event.message.text.strip()
        user_id = event.source.user_id
        print(f"Received message from user_id: {user_id}") # Debug print

        # 獲取使用者 Line 顯示名稱
        profile = self.line_bot_api.get_profile(user_id)
        display_name = profile.display_name

        # 確保使用者存在於資料庫中，並更新顯示名稱
        self.user_manager.get_or_create_user(user_id, display_name) # Call get_or_create_user with display_name

        try:
            # 檢測冷啟動狀態
            if self.app_state and self.app_state.is_cold_start():
                print(f"冷啟動期間收到訊息: {user_message}")
                self.reply_message_flex(event.reply_token,
                    "🚀 系統剛啟動完成！\n請重新發送您的訊息，我現在準備好了 😊")
                return

            # 正常的訊息解析流程
            parsed_data = self.message_parser.parse(user_message)
            
            response_message = self.message_handler.handle_user_message(user_id, user_message, parsed_data)

            self.reply_message_flex(event.reply_token, response_message)

        except Exception as e:
            print(f"LINE Bot 錯誤: {e}")

            # 出錯時清除狀態
            self.user_state_manager.clear_user_state(user_id)
            # 如果是啟動期間的錯誤，可能是資源尚未載入
            error_msg = "系統正在啟動中，請稍後重新發送訊息" if self.app_state.is_cold_start() else "抱歉，系統暫時無法處理，請稍後再試"
            self.reply_message_flex(event.reply_token, error_msg)
        
    def get_help_message(self):
        """取得幫助訊息"""
        base_message =  """歡迎使用個人財務助手！

        支援功能：
        💰 記帳：
        • "午餐花了150"
        • "買咖啡50元"
        • "薪水入帳30000"

        📊 查詢：
        • "查詢本月支出"
        • "我的資產"

        範例：
        早餐花80元、搭捷運30、薪水45000"""
        
        #若是冷啟動期間，加入提示
        if self.app_state.is_cold_start():
            base_message += "\n\n💡 提示：系統剛啟動，如無回應請重新發送"
        return base_message

    def reply_message_flex(self, reply_token, message):
        """支援 Flex Message 的回覆方法"""
        try:
            if isinstance(message, str):
                # 文字訊息
                self.line_bot_api.reply_message(
                    reply_token,
                    TextSendMessage(text=message)
                )
            else:
                self.line_bot_api.reply_message(reply_token, message)

        except LineBotApiError as e:
            print(f"Line API Error: {e}")

    def push_message_flex(self, user_id, message):
        """支援 Flex Message 的推送方法"""
        try:
            if isinstance(message, str):
                # 文字訊息
                self.line_bot_api.push_message(
                    user_id,
                    TextSendMessage(text=message)
                )
            else:
                self.line_bot_api.push_message(user_id, message)
        except LineBotApiError as e:
            print(f"Line Push Error: {e}")

    def verify_webhook(self, body, signature):
        """驗證 webhook 簽名"""
        try:
            self.handler.handle(body, signature)
            return True
        except InvalidSignatureError:
            return False
