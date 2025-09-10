import os
import json
from models.schema import budget_categories_table
from models.database import engine
from sqlalchemy import select
from datetime import datetime
import google.generativeai as genai
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, 
    QuickReply, QuickReplyButton, MessageAction,
    FlexSendMessage
)

class LineBotManager:
    def __init__(self, budget_manager=None, asset_manager=None):
        #Line Bot設定
        self.line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
        self.handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
        
        #依賴注入現有 managers
        self.budget_manager = budget_manager
        self.asset_manager = asset_manager

        # Gemini設定
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('models/gemini-1.5-flash')

        # 註冊事件處理器
        self.register_handlers()

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

        類別限制：餐飲、交通、購物、娛樂、醫療、教育、投資、生活、其他

        注意：只回傳純 JSON，不要 markdown 標記
        """

    def register_handlers(self):
        """註冊 Line Bot 事件處理器"""
        @self.handler.add(MessageEvent, message=TextMessage)
        def handle_text_message(event):
            self.handle_message_flex(event)

    def handle_message_flex(self, event):
        """支援 Flex Message 的訊息處理"""
        user_message = event.message.text.strip()
        user_id = event.source.user_id

        try:
            parsed_data = self.parse_with_gemini(user_message)

            if parsed_data.get("type") == "expense":
                response_message = self.handle_expense_with_flex(parsed_data, user_id)
            else:
                response_message = self.process_parsed_message(parsed_data, user_id)
            
            self.reply_message_flex(event.reply_token, response_message)

        except Exception as e:
            print(f"LINE Bot 錯誤: {e}")
            error_msg = "抱歉，系統暫時無法處理，請稍後再試"
            self.reply_message_flex(event.reply_token, error_msg)
            

    def parse_with_gemini(self, message):
        """使用 Gemini 解析自然語言"""
        try:
            prompt = self.prompt_template.format(message = message)
            response = self.model.generate_content(prompt)

            # 清理回應
            cleaned_text = self._clean_response(response.text)
            result = json.loads(cleaned_text)

            return self._validate_result(result, message)
        
        except Exception as e:
            print(f"Gemini 解析失敗: {e}")
            return {"type": "other", "error": str(e)}
        
    def process_parsed_message(self, parsed_data, user_id):
        """處理解析後的訊息"""
        message_type = parsed_data.get("type")

        if message_type == "expense":
            return self.handle_expense_with_flex(parsed_data, user_id)
        elif message_type == "income":
            return self.handle_income(parsed_data, user_id)
        elif message_type == "query":
            return self.handle_query(user_id)
        elif message_type == "asset_query":
            return self.handle_asset_query(user_id)
        else:
            return self.get_help_message()
        
    def handle_expense_with_flex(self, data, user_id):
        """使用 Flex Message 處理支出"""
        try:
            # 使用現有的 budget_manager
            success, message = self.budget_manager.add_transaction(
                date = datetime.now().strftime("%Y-%m-%d"),
                item = data.get("description", "Line記帳"),
                amount = data["amount"],
                transaction_type = "expense",
                budget_category = data["category"],
                description = f"LINE Bot: {data.get('description', '')}"
            )

            if success:
                return self._format_expense_success_flex(data)
            else:
                return f"紀錄失敗:{message}"
            
        except Exception as e:
            return f"紀錄失敗: {str(e)}"
        
    def handle_income(self, data, user_id):
        """處理收入紀錄"""
        try:
            success, message = self.budget_manager.add_transaction(
                date = datetime.now().strftime("%Y-%m-%d"),
                item = data.get("description", "Line收入"),
                amount = data["amount"],
                transaction_type = "income",
                budget_category = "收入",
                description = f"LINE Bot: {data.get('description', '')}"
            )
            if success:
                return self._format_income_success(data)
            else:
                return f"紀錄失敗:{message}"
            
        except Exception as e:
            return f"紀錄失敗: {str(e)}"
        
    def handle_query(self, user_id):
        """處理查詢請求"""
        try:
            # 獲取本月支出統計
            current_month = datetime.now().strftime("%Y-%m")
            expenses = self.budget_manager.calculate_monthly_expenses(current_month)

            if not expenses:
                return f"本月尚無支出紀錄"
            
            # 格式化回覆
            reply = f"【{current_month} 支出統計】 \n"
            total = 0
            for category, amount in expenses.items():
                reply += f"· {category}: ${amount:,.0f}\n"
                total += amount

            reply += f"\n總支出: ${total:,.0f}"
            return reply
        except Exception as e:
            return f"查詢失敗:{str(e)}"
        
    def handle_asset_query(self, user_id):
        """處理資產查詢"""
        try:
            totals = self.asset_manager.calculate_totals()

            reply = "【資產總攬】\n"
            reply += f"總資產: ${totals.get('總資產', 0):,.0f}\n\n"

            for asset_type, amount in totals.items():
                if asset_type != '總資產' and amount > 0:
                    reply += f"·{asset_type}: ${amount:,.0f}\n"

            return reply
        except Exception as e:
            return f"查詢失敗:{str(e)}"
        
    def _format_expense_success_flex(self, data):
        """使用 Flex Message 格式化支出成功訊息"""
        category = data.get("category", "其他")
        amount = data.get("amount", 0)
        description = data.get("description", "記帳")
        date = datetime.now().strftime("%Y/%m/%d")

        #類別顏色對應
        category_color = {
            "餐飲": "#4CAF50",
            "交通": "#2196F3", 
            "購物": "#FF9800",
            "娛樂": "#E91E63",
            "醫療": "#F44336",
            "投資": "#607D8B",
            "生活": "#795548",
            "其他": "#9E9E9E"
        }

        selected_color = category_color.get(category, "#9E9E9E")

        #獲取預算狀況
        budget_status = self._get_budget_status_for_flex(category)

        flex_content = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": category,
                            "weight": "bold",
                            "color": "#FFFFFF",
                            "size": "sm"
                        },
                        {
                            "type": "text",
                            "text": "記帳成功",
                            "weight": "bold",
                            "color": "#FFFFFF",
                            "size": "xs",
                            "align": "end"
                        }
                    ],
                    "backgroundColor": selected_color,
                    "paddingAll": "12px",
                    "cornerRadius": "8px",
                    "margin": "none"
                },
                {
                    "type": "text",
                    "text": f"${amount:,}",
                    "weight": "bold",
                    "size": "4xl",
                    "margin": "lg",
                    "color": "#333333"
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "lg",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "baseline",
                            "spacing": "sm",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "備註",
                                    "color": "#999999",
                                    "size": "sm",
                                    "flex": 1
                                },
                                {
                                    "type": "text",
                                    "text": description,
                                    "wrap": True,
                                    "color": "#666666",
                                    "size": "sm",
                                    "flex": 3
                                }
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "baseline",
                            "spacing": "sm",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "日期",
                                    "color": "#999999",
                                    "size": "sm",
                                    "flex": 1
                                },
                                {
                                    "type": "text",
                                    "text": date,
                                    "wrap": True,
                                    "color": "#666666",
                                    "size": "sm",
                                    "flex": 3
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    }
        if budget_status:
            flex_content["body"]["contents"].append({
                "type": "separator",
                "margin": "lg"
            })
            flex_content["body"]["contents"].append({
                "type": "box",
                "layout": "vertical",
                "margin": "lg",
                "contents": [
                    {
                        "type": "text",
                        "text": budget_status["title"],
                        "size": "sm",
                        "color": budget_status["color"],
                        "weight": "bold"
                    },
                    {
                        "type": "text",
                        "text": budget_status["message"],
                        "size": "xs",
                        "color": "#666666",
                        "wrap": True,
                        "margin": "xs"
                    }
                ]
            })

        flex_content["footer"] = {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "link",
                    "height": "sm",
                    "action": {
                        "type": "message",
                        "label": "查看本月支出",
                        "text": "查詢本月支出"
                    }
                },
                {
                    "type": "button",
                    "style": "link", 
                    "height": "sm",
                    "action": {
                        "type": "message",
                        "label": "查看資產狀況",
                        "text": "我的資產"
                    }
                }
            ]
        }
        
        return FlexSendMessage(
            alt_text=f"{category} ${amount:,} 記帳成功",
            contents=flex_content
        )
    
    def _get_budget_status_for_flex(self, category):
        """獲取預算狀況用於 Flex Message"""
        try:
            current_month = datetime.now().strftime("%Y-%m")

            stmt = select(budget_categories_table).where(
                budget_categories_table.c.month == current_month,
                budget_categories_table.c.category_name == category
            )

            with engine.connect() as conn:
                budget_result = conn.execute(stmt).first()
                if not budget_result:
                    return None
                
            budget_amount = float(budget_result.amount)

            #計算已花費
            expenses = self.budget_manager.calculate_monthly_expenses(current_month)
            spent = expenses.get(category, 0)
            remaining = budget_amount - spent
            usage_rate = (spent / budget_amount) * 100

            #根據使用率回應
            if usage_rate >= 100:
                return {
                    "title": "⚠️ 預算超支",
                    "message": f"已超支 ${abs(remaining):,}",
                    "color": "#F44336"
                }
            elif usage_rate >= 80:
                return {
                    "title": "⚠️ 預算警告", 
                    "message": f"剩餘 ${remaining:,} ({100-usage_rate:.0f}%)",
                    "color": "#FF9800"
                }
            elif usage_rate >= 50:
                return {
                    "title": "✅ 預算正常",
                    "message": f"剩餘 ${remaining:,} ({100-usage_rate:.0f}%)",
                    "color": "#4CAF50"
                }
            else:
                return {
                    "title": "✅ 預算充足",
                    "message": f"剩餘 ${remaining:,}",
                    "color": "#4CAF50"
                }
        except Exception as e:
            return None
    
    def _format_income_success(self, data):
        return f"收入記錄成功！\n💰 金額：${data['amount']:,}\n📝 描述：{data['description']}"


    def get_help_message(self):
        """取得幫助訊息"""
        return """歡迎使用個人財務助手！

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

    def _clean_response(self, text):
        """清理 Gemini 回應"""
        cleaned = text.strip()
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]
        elif cleaned.startswith('```'):
            cleaned = cleaned[3:]
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        return cleaned.strip()

    def _validate_result(self, result, original_message):
        """驗證解析結果"""
        if "type" not in result:
            result["type"] = "other"

        if result["type"] == "expense":
            if "amount" not in result or not isinstance(result["amount"], (int, float)):
                result["type"] = "other"
                result["error"] = "無法識別金額"

            if "category" not in result:
                result["category"] = "其他"
            if "description" not in result:
                result["description"] = original_message[:20]

        elif result["type"] == "income":
            if "amount" not in result or not isinstance(result["amount"], (int, float)):
                result["type"] = "other"
                result["error"] = "無法識別收入金額"
            if "description" not in result:
                result["descripttion"] = original_message[:20]

        return result

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