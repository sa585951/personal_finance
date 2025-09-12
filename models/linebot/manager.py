import os
import google.generativeai as genai
from datetime import datetime
from .message_handler import MessageHandler
from .message_parser import MessageParser
from .user_state_manager import UserStateManager
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, 
    FlexSendMessage
)

class LineBotManager:
    def __init__(self, budget_manager=None, asset_manager=None, app_state=None):

        self.app_state = app_state
        #Line Bot設定
        self.line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
        self.handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
        
        # Gemini設定
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('models/gemini-1.5-flash')

        #依賴注入現有 managers
        self.user_state_manager = UserStateManager()
        # Prompt模板
        self.prompt_template = """
        分析以下中文記帳訊息，回傳 JSON 格式：

        訊息："{message}"

        規則：
        1. 支出記錄：{{"type": "expense", "category": "類別", "amount": 數字, "description": "簡短描述"}}
        2. 收入記錄：{{"type": "income", "amount": 數字, "description": "簡短描述"}}
        3. 查詢請求：{{"type": "query", "action": "查詢類型"}}
        4. 資產查詢：{{"type": "asset_query"}}
        5. 非記帳訊息：{{"type": "other"}}

        類別限制：伙食、交通、購物、娛樂、醫療、投資、生活、其他

        注意：只回傳純 JSON，不要 markdown 標記
        """

        #注入Message Parser
        self.message_parser = MessageParser(
            gemini_model=self.model,
            prompt_template=self.prompt_template,
        )

        # 建立 Handler實例
        self.message_handler = MessageHandler(budget_manager, asset_manager, self.user_state_manager)
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
            error_msg = "系統正在啟動中，請稍後重新發送訊息" if self._is_cold_start() else "抱歉，系統暫時無法處理，請稍後再試"
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
        if self._is_cold_start():
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
