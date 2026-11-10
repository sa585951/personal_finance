# models/linebot/manager.py

import os
import logging
from google import genai
from google.genai import types
from sqlalchemy.orm import sessionmaker
from .oral_pilot import LineOralPilot
from .message_parser import MessageParser
from ..ai_parse_event_manager import AIParseEventManager
from ..user_manager import UserManager
from .webhook_events import LineWebhookEvents
from .notice import create_notice_message
from ..optional_access import load_optional_access
from ..line_ai_gateway import LineAIGateway, read_line_ai_budget, read_line_ai_daily_limit
from linebot.v3 import WebhookParser
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    PushMessageRequest,
    ReplyMessageRequest,
)
from linebot.v3.messaging.exceptions import ApiException


class GeminiModelAdapter:
    """讓新版 Google GenAI SDK 維持既有 GeminiParser 需要的介面。"""

    def __init__(self, client, model_name):
        self.client = client
        self.model_name = model_name

    def generate_content(self, prompt):
        # Enforce containment at the shared outbound boundary, not just Web UI.
        if not load_optional_access(os.environ).cloud_ai:
            raise RuntimeError("Cloud AI is paused pending G-AI validation")
        return self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )


class MissingGeminiModel:
    """Gemini API key 未設定時，讓本地 fallback 有機會處理基本輸入。"""

    def generate_content(self, prompt):
        raise RuntimeError("GEMINI_API_KEY is not configured")


class LineBotManager:
    """
    管理 Line Bot 的核心邏輯，包含訊息的接收、解析與回覆。
    現在的設計是作為一個較無狀態的服務，由 web_app 傳入 db_session 來處理請求。
    """
    def __init__(self, app_state, db_session):
        self.app_state = app_state
        self.db_session = db_session
        # Line Bot 設定
        self.line_api_client = ApiClient(
            Configuration(access_token=os.getenv("LINE_MSG_CHANNEL_ACCESS_TOKEN"))
        )
        self.line_bot_api = MessagingApi(self.line_api_client)
        self.parser = WebhookParser(os.getenv("LINE_MSG_CHANNEL_SECRET"))
        
        # Gemini 設定
        self.gemini_model_name = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_client = (genai.Client(api_key=gemini_api_key)
                              if gemini_api_key and load_optional_access(os.environ).cloud_ai else None)
        self.model = (
            GeminiModelAdapter(self.gemini_client, self.gemini_model_name)
            if self.gemini_client
            else MissingGeminiModel()
        )

        self.line_ai_gateway = None
        budget = read_line_ai_budget(os.environ)
        daily_limit = read_line_ai_daily_limit(os.environ)
        paid_project_verified = os.getenv("NOMICA_LINE_AI_PAID_PROJECT_VERIFIED") == "true"
        admin_line_user = (os.getenv("NOMICA_ADMIN_LINE_USER_ID") or "").strip()
        if (budget is not None and daily_limit is not None and gemini_api_key and paid_project_verified
                and load_optional_access(os.environ).line_oral_pilot):
            # Provider retries could charge twice for one reservation.
            client = genai.Client(api_key=gemini_api_key, vertexai=False, http_options=types.HttpOptions(
                timeout=8_000, retry_options=types.HttpRetryOptions(attempts=1),
            ))
            notify = (lambda text: self.push_message_flex(admin_line_user, text)) if admin_line_user else None
            self.line_ai_gateway = LineAIGateway(sessionmaker(bind=db_session.get_bind()), client.models, budget,
                                                 daily_limit=daily_limit, notify=notify)

        self.user_manager = UserManager(self.db_session)
        self.ai_parse_event_manager = AIParseEventManager(self.db_session)
        
        # Prompt 模板 (保持不變)
        self.prompt_template = '''
        分析以下中文記帳訊息，並嚴格回傳 JSON 格式。

        訊息："{message}"

        **輸出欄位定義:**
        - `budget_category`: 最高層級的分類，必須是「類別限制」中的一個。
        - `category`: 交易項目名稱，優先填入使用者要查找或分類的項目，例如「午餐」、「晚餐」、「拉麵」、「計程車」、「薪資」。
        - `description`: 店家、品牌或使用者明確提供的補充備註，例如「麥當勞」、「跟朋友聚餐」、「公司報銷」。如果沒有店家或明確備註，請回傳空字串 "" 或 null，不要把原始訊息整段放入。
        - `amount`: 金額 (數字)。
        - `currency`: 訊息中的幣別代碼，例如 TWD、JPY、USD、EUR、KRW。若未提到幣別，此欄位為 null。
        - `target_asset`: 支付的資產/帳戶。若使用者有寫具名帳戶，例如「國泰信用卡」，必須保留完整名稱，不可只回傳「信用卡」。如果訊息中沒有提到，此欄位為 null。

        **規則：**
        1. **支出記錄**: 必須包含 `type`, `budget_category`, `category`, `amount`。
           - JSON: {{ "type": "expense", "budget_category": "...", "category": "...", "description": "...", "amount": ..., "target_asset": "..." }}
        2. **收入記錄**: 
           - JSON: {{ "type": "income", "budget_category": "收入", "category": "收入來源", "description": "可選備註", "amount": ..., "target_asset": "..." }}
        3. **欄位提取邏輯**: 
           - `budget_category`: 將消費目的歸類到「類別限制」中的一個。
           - `category`: 從訊息中提取最適合作為列表顯示與使用者回查的項目名稱；例如「午餐麥當勞 150」的 category 是「午餐」。
           - `description`: 放店家、品牌或額外補充備註；例如「午餐麥當勞 150」的 description 是「麥當勞」。帳戶名稱只放在 `target_asset`，不可重複放入 description。若沒有店家或明確備註，留空，不要填入 category，也不要填入原始訊息。
           - `currency`: 若訊息提到「日幣、日圓、JPY」回傳 JPY；「台幣、TWD、NTD」回傳 TWD；「美金、美元、USD」回傳 USD；未提到則回傳 null。
           - `target_asset`: 從訊息中提取支付方式或完整帳戶名稱，如「用現金」、「國泰信用卡」、「從郵局轉帳」。
        4. **其他請求**: 根據訊息類型回傳對應的 JSON 結構。
        5. **投資投入 / 定期定額**: 例如「定期定額 5000」、「買 ETF 10000」屬於帳戶間資金流向，不要解析成 expense；請回傳 {{ "type": "other", "error": "investment_allocation_requires_transfer" }}。

        **類別限制 (用於 budget_category):**
        伙食、交通、購物、娛樂、醫療、工作、生活、其他、收入

        **精選範例:**
        - 訊息: "午餐吃麥當勞 150元 用國泰信用卡"
          應解析為: {{ "type": "expense", "budget_category": "伙食", "category": "午餐", "description": "麥當勞", "amount": 150, "currency": "TWD", "target_asset": "國泰信用卡" }}
        - 訊息: "永豐日幣活存扣拉麵 1200 日圓"
          應解析為: {{ "type": "expense", "budget_category": "伙食", "category": "拉麵", "description": "", "amount": 1200, "currency": "JPY", "target_asset": "永豐活存" }}
        - 訊息: "在7-11買了可口可樂，付了現金30元"
          應解析為: {{ "type": "expense", "budget_category": "伙食", "category": "可口可樂", "description": "", "amount": 30, "target_asset": "現金" }}
        - 訊息: "搭計程車回家花了 250"
          應解析為: {{ "type": "expense", "budget_category": "交通", "category": "計程車", "description": "", "amount": 250, "target_asset": null }}
        - 訊息: "治裝費 3000"
          應解析為: {{ "type": "expense", "budget_category": "購物", "category": "治裝費", "description": "", "amount": 3000, "target_asset": null }}
        - 訊息: "公司代墊影印費 120"
          應解析為: {{ "type": "expense", "budget_category": "工作", "category": "影印費", "description": "公司代墊", "amount": 120, "target_asset": null }}


        注意：只回傳純 JSON，不要 markdown 標記。
        '''

        self.message_parser = MessageParser(
            gemini_model=self.model,
            prompt_template=self.prompt_template,
        )

    def process_oral_event(self, event):
        pilot = LineOralPilot(
            self.db_session, self.message_parser.ai_parse_service, getattr(self, "line_ai_gateway", None),
        )
        return LineWebhookEvents(self.db_session).process(event, pilot.handle)

    def reply_message_flex(self, reply_token, message, raise_on_error=False):
        """
        支援 Flex Message 的回覆方法
        """
        try:
            self.line_bot_api.reply_message(
                ReplyMessageRequest(
                    replyToken=reply_token,
                    messages=[self._to_line_message(message)],
                )
            )
        except ApiException as e:
            if raise_on_error:
                raise
            logging.getLogger(__name__).warning("LINE reply failed: type=%s", type(e).__name__)

    def push_message_flex(self, user_id, message):
        """
        支援 Flex Message 的推送方法
        """
        try:
            self.line_bot_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[self._to_line_message(message)],
                )
            )
        except ApiException as e:
            logging.getLogger(__name__).warning("LINE push failed: type=%s", type(e).__name__)

    def _to_line_message(self, message):
        """把舊流程的純文字輸出統一轉成 Flex 卡片。"""
        if isinstance(message, str):
            return create_notice_message("通知", message)
        return message
