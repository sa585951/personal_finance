import os
import json
import time
from models.schema import budget_categories_table
from models.schema import transactions_table
from models.database import engine
from sqlalchemy import select, desc, func
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

        self._startup_time = time.time()
        self._is_warming_up = True
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

        類別限制：伙食、交通、購物、娛樂、醫療、投資、生活、其他

        注意：只回傳純 JSON，不要 markdown 標記
        """

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
            if self._is_cold_start():
                print(f"檢測到冷啟動，訊息: {user_message}")
                self.reply_message_flex(event.reply_token,
                    "🚀 系統剛啟動完成！\n請重新發送您的訊息，我現在準備好了 😊")
                return

            parsed_data = self.parse_with_gemini(user_message)

            if parsed_data.get("type") == "expense":
                response_message = self.handle_expense_with_flex(parsed_data, user_id)
            else:
                response_message = self.process_parsed_message(parsed_data, user_id)
            
            self.reply_message_flex(event.reply_token, response_message)

        except Exception as e:
            print(f"LINE Bot 錯誤: {e}")

            # 如果是啟動期間的錯誤，可能是資源尚未載入
            if self._is_cold_start():
                error_msg = "系統正在啟動中，請稍後重新發送訊息"
            else:
                error_msg = "抱歉，系統暫時無法處理，請稍後再試"

            self.reply_message_flex(event.reply_token, error_msg)
            

    def parse_with_gemini_original(self, message):
        """使用 Gemini 解析自然語言"""
        try:
            # 紀錄是否在冷啟動期間使用 Gemini
            if self._is_cold_start():
                print(f"冷啟動期間呼叫 Gemini: {message}")

            prompt = self.prompt_template.format(message = message)
            response = self.model.generate_content(prompt)

            # 清理回應
            cleaned_text = self._clean_response(response.text)
            result = json.loads(cleaned_text)

            return self._validate_result(result, message)
        
        except Exception as e:
            print(f"Gemini 解析失敗: {e}")

            # 冷啟動期間的特殊處理
            if self._is_cold_start():
                print("冷啟動期間 Gemini 失敗， 可能是網路連線還沒穩定")

            return {"type": "other", "error": str(e)}
    
    def parse_with_gemini(self, message):
        return self.parse_message_hybrid(message)
    
    def parse_message_hybrid(self, message):
        """混和解析策略"""
        quick_result = self._quick_parse(message)
        if quick_result:
            return quick_result
        
        return self.parse_with_gemini_original(message)

    def _quick_parse(self, message):
        """快速解析規則"""
        message_lower = message.lower()

        #查詢類 - 直接匹配
        if any(word in message_lower for word in ['查詢', '統計', '支出', '本月']):
            return {"type": "query"}
        
        if any(word in message_lower for word in ['資產', '總資產', '餘額']):
            return {"type": "asset_query"}
        
        if any(word in message_lower for word in ['幫助', '說明', '功能', '測試']):
            return {"type": "other"}
        
        #記帳類 - 讓 Gemini 處理(返回 None 表示需要 Gemini)
        if any(char.isdigit() for char in message):
            return None #交給 Gemini 處理
        
        # 其他 - 預設為幫助
        return {"type": "other"}

    def process_parsed_message(self, parsed_data, user_id):
        """處理解析後的訊息"""
        message_type = parsed_data.get("type")

        if message_type == "expense":
            return self.handle_expense_with_flex(parsed_data, user_id)
        elif message_type == "income":
            return self.handle_income_with_flex(parsed_data, user_id)
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
                description = f"{data.get('description', '')}"
            )

            if success:
                return self._format_expense_success_flex(data)
            else:
                return f"紀錄失敗:{message}"
            
        except Exception as e:
            return f"紀錄失敗: {str(e)}"
        
    def handle_income_with_flex(self, data, user_id):
        """使用 Flex Message 處理收入"""
        try:
            success, message = self.budget_manager.add_transaction(
                date=datetime.now().strftime("%Y-%m-%d"),
                item=data.get("description", "Line收入"),
                amount=data["amount"],
                transaction_type="income",
                budget_category="收入",
                description=f"{data.get('description', '')}"
            )
            
            if success:
                return self._format_income_success_flex(data)
            else:
                return f"記錄失敗: {message}"
                
        except Exception as e:
            return f"記錄失敗: {str(e)}"
        
    def handle_query(self, user_id):
        """處理查詢請求 - 改用 Flex Message"""
        try:
            return self._handle_query_with_flex(user_id)
        except Exception as e:
            return f"查詢失敗:{str(e)}"
        
    def _handle_query_with_flex(self, user_id):
        """使用 Flex Message 處理查詢統計"""
        try:
            current_month = datetime.now().strftime("%Y-%m")
            expenses = self.budget_manager.calculate_monthly_expenses(current_month)

            if not expenses:
                return "本月尚無支出記錄"
            
            # 獲取詳細交易記錄
            recent_transactions = self._get_recent_transactions(current_month, limit=5)
            total_expenses = sum(expenses.values())
            transaction_count = self._get_all_month_transactions(current_month)

            category_stats = self._get_category_expenses(current_month)

            return self._create_monthly_summary_flex(current_month, total_expenses, transaction_count, recent_transactions, category_stats)
        except Exception as e:
            return f"查詢失敗: {str(e)}"
        
    
    def _get_recent_transactions(self, month, limit=5):
        """獲取最近交易記錄"""
        try:
            stmt = select(transactions_table).where(
                func.to_char(transactions_table.c.date, 'YYYY-MM') == month,
                transactions_table.c.type == 'expense'
            ).order_by(desc(transactions_table.c.date)).limit(limit)

            with engine.connect() as conn:
                result = conn.execute(stmt)
                return [dict(row._mapping) for row in result]
            
        except Exception as e:
            print(f"獲取交易記錄失敗: {e}")
            return []

    def _get_all_month_transactions(self, month):
        """獲取整月交易數量"""
        try:
            stmt = select(func.count(transactions_table.c.id)).where(
                func.to_char(transactions_table.c.date, 'YYYY-MM') == month,
                transactions_table.c.type == 'expense'
            )

            with engine.connect() as conn:
                result = conn.execute(stmt).scalar()
                return result if result else 0
            
        except Exception as e:
            return 0
        
    def _get_category_expenses(self, month):
        """獲取分類支出統計"""
        try:
            stmt = select(transactions_table.c.budget_category,
                func.sum(transactions_table.c.amount).label('total'),
                func.count(transactions_table.c.id).label('count')
            ).where(
                func.to_char(transactions_table.c.date, 'YYYY-MM') == month,
                transactions_table.c.type == 'expense'
            ).group_by(transactions_table.c.budget_category).order_by(
                func.sum(transactions_table.c.amount).desc()
            )

            with engine.connect() as conn:
                result = conn.execute(stmt)
                return [
                    {
                        'category': row.budget_category,
                        'total': float(row.total),
                        'count': row.count
                    }
                    for row in result
                ]
        except Exception as e:
            print(f"獲取分類統計失敗: {e}")
            return []

    def _create_monthly_summary_flex(self, month, total, count, transactions, category_stats):
        """建立月度統計 Flex Message"""
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"{month}",
                                "size": "sm",
                                "color": "#666666"
                            },
                            {
                                "type": "text", 
                                "text": f"共 {count} 筆記錄",
                                "size": "sm",
                                "color": "#666666",
                                "align": "end"
                            }
                        ]
                    },
                    {
                        "type": "text",
                        "text": "支出統計",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#FF6B35",
                        "margin": "sm"
                    },
                    {
                        "type": "text",
                        "text": f"${total:,}",
                        "weight": "bold", 
                        "size": "3xl",
                        "color": "#333333",
                        "margin": "xs"
                    }
                ],
                "backgroundColor": "#F8F9FA",
                "paddingAll": "16px"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": []
            }
        }

        if category_stats:
            flex_content["body"]["contents"].append({
                "type": "text",
                "text": "分類統計",
                "weight": "bold",
                "size": "md",
                "color": "#333333",
                "margin": "lg"
            })

            #分類統計表頭
            flex_content["body"]["contents"].append({
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {"type": "text", "text": "類別", "size": "sm", "color": "#999999", "flex": 2},
                    {"type": "text", "text": "筆數", "size": "sm", "color": "#999999", "flex": 1, "align": "center"},
                    {"type": "text", "text": "金額", "size": "sm", "color": "#999999", "align": "end", "flex": 2}
                ],
                "margin": "md"
            })

            #分類統計內容
            for stat in category_stats:
                category_row = {
                    "type": "box",
                    "layout": "horizontal", 
                    "contents": [
                        {
                            "type": "text",
                            "text": stat['category'],
                            "size": "sm",
                            "color": "#333333",
                            "flex": 2
                        },
                        {
                            "type": "text",
                            "text": f"{stat['count']}筆",
                            "size": "sm",
                            "color": "#666666",
                            "flex": 1,
                            "align": "center"
                        },
                        {
                            "type": "text",
                            "text": f"${stat['total']:,.0f}",
                            "size": "sm",
                            "color": "#333333",
                            "align": "end",
                            "flex": 2
                        }
                    ],
                    "margin": "sm",
                    "backgroundColor": "#F0F7FF",
                    "paddingAll": "8px",
                    "cornerRadius": "4px"
                }
                flex_content["body"]["contents"].append(category_row)
            
            #分隔線
            flex_content["body"]["contents"].append({
                "type": "separator",
                "margin": "lg"
            })

        # 最近交易記錄
        flex_content["body"]["contents"].append({
            "type": "text",
            "text": "最近交易",
            "weight": "bold",
            "size": "md",
            "color": "#333333",
            "margin": "lg"
        })

        flex_content["body"]["contents"].append({
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {"type": "text", "text": "日期", "size": "sm", "color": "#999999", "flex": 1},
                {"type": "text", "text": "類別", "size": "sm", "color": "#999999", "flex": 2},
                {"type": "text", "text": "金額", "size": "sm", "color": "#999999", "align": "end", "flex": 1}
            ],
            "margin": "md"
        })

        #加入交易明細
        for transaction in transactions:
            date_str = str(transaction['date'])[-5:] if 'date' in transaction else "N/A"
            category = transaction.get('budget_category', 'N/A')
            amount = transaction.get('amount', 0)

            transaction_row = {
                "type": "box",
                "layout": "horizontal", 
                "contents": [
                    {
                        "type": "text",
                        "text": date_str,
                        "size": "sm",
                        "color": "#333333",
                        "flex": 1
                    },
                    {
                        "type": "text", 
                        "text": category,
                        "size": "sm",
                        "color": "#333333",
                        "flex": 2
                    },
                    {
                        "type": "text",
                        "text": f"${amount:,}",
                        "size": "sm",
                        "color": "#333333",
                        "align": "end",
                        "flex": 1
                    }
                ],
                "margin": "sm",
                "backgroundColor": "#F0F7FF" if amount > 200 else "#FFFFFF",
                "paddingAll": "8px",
                "cornerRadius": "4px"
            }
            flex_content["body"]["contents"].append(transaction_row)
        
        return FlexSendMessage(
            alt_text=f"{month} 支出統計 ${total:,}",
            contents=flex_content
        )
        
    def handle_asset_query(self, user_id):
        """處理資產查詢"""
        try:
            totals = self.asset_manager.calculate_totals()
            return self._create_asset_overview_flex(totals)
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
            "伙食": "#4CAF50",
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
    
    def _format_income_success_flex(self,data):
        """使用 Flex Message 格式化收入成功訊息"""
        amount = data.get("amount", 0)
        description = data.get("description", "收入")
        date = datetime.now().strftime("%Y/%m/%d")

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
                                "text": "收入",
                                "weight": "bold",
                                "color": "#FFFFFF",
                                "size": "sm"
                            },
                            {
                                "type": "text",
                                "text": "記錄成功",
                                "weight": "bold",
                                "color": "#FFFFFF",
                                "size": "xs",
                                "align": "end"
                            }
                        ],
                        "backgroundColor": "#4CAF50",  # 綠色表示收入
                        "paddingAll": "12px",
                        "cornerRadius": "8px",
                        "margin": "none"
                    },
                    {
                        "type": "text",
                        "text": f"+${amount:,}",  # 加上 + 號表示收入
                        "weight": "bold",
                        "size": "4xl",
                        "margin": "lg",
                        "color": "#4CAF50"  # 綠色金額
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
            },
            "footer": {
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
        }
        
        return FlexSendMessage(
            alt_text=f"收入 +${amount:,} 記錄成功",
            contents=flex_content
        )
    
    def _create_asset_overview_flex(self, totals):
        """建立資產總攬 Flex Message"""
        total_assets = totals.get('總資產', 0 )

        #資產類型顏色對應
        asset_colors = {
            "活存": "#4CAF50",
            "定存": "#2196F3",
            "投資": "#FF9800",
            "其他": "#9E9E9E"
        }

        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents":[
                    {
                        "type": "text",
                        "text": "資產總攬",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#333333"
                    },
                    {
                        "type": "text",
                        "text": f"${total_assets:,.0f}",
                        "weight": "bold",
                        "size": "4xl",
                        "color": "#4CAF50",
                        "margin": "md"
                    },
                    {
                        "type": "text",
                        "text": f"更新時間: {datetime.now().strftime('%Y/%m/%d %H:%M')}",
                        "size": "xs",
                        "color": "#999999",
                        "margin": "sm"
                    }
                ],
                "backgroundColor": "#F8F9FA",
                "paddingAll": "20px"
            },
            "body":{
                "type": "box",
                "layout": "vertical",
                "contents": []
            }
        }

        # 過濾出有金額的資產類型
        active_assets = {k: v for k, v in totals.items()
                        if k != '總資產' and v > 0}
        
        if active_assets:
            #資產分布標題
            flex_content["body"]["contents"].append({
                "type": "text",
                "text": "資產分布",
                "weight": "bold",
                "size": "md",
                "color": "#333333",
                "margin": "lg"
            })
        
            # 資產分布列表
            for asset_type, amount in active_assets.items():
                percentage = (amount / total_assets * 100) if total_assets > 0 else 0
                color = asset_colors.get(asset_type, "#9E9E9E")

                # 資產項目
                asset_row = {
                    "type": "box",
                    "layout": "horizontal",
                    "contents":[
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents":[
                                {
                                    "type": "text",
                                    "text": asset_type,
                                    "weight": "bold",
                                    "size": "sm",
                                    "color": "#333333"
                                },
                                {
                                    "type": "text",
                                    "text": f"{percentage:.1f}%",
                                    "size": "xs",
                                    "color": "#666666"
                                }
                            ],
                            "flex": 2
                        },
                        {
                            "type": "text",
                            "text": f"${amount:,.0f}",
                            "size": "sm",
                            "color": "#333333",
                            "align": "end",
                            "weight": "bold",
                            "flex": 2
                        }
                    ],
                    "margin": "md",
                    "backgroundColor": "#FFFFFF",
                    "paddingAll": "12px",
                    "cornerRadius": "8px",
                    "borderWidth": "2px",
                    "borderColor": color
                }

                flex_content["body"]["contents"].append(asset_row)
        else:
            #沒有資產時的提示
            flex_content["body"]["contents"].append({
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "尚未新增任何資產",
                        "size": "sm",
                        "color": "#999999",
                        "align": "center",
                        "margin": "sm"
                    },
                    {
                        "type": "text",
                        "text": "點擊下方按鈕開始管理您的資產",
                        "size": "sm",
                        "color": "#999999",
                        "align": "center",
                        "margin": "sm"
                    }
                ],
                "margin": "lg",
                "paddingAll": "20px"
            })
        
        # 操作按鈕
        flex_content["footer"] = {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "height": "sm",
                    "color": "#4CAF50",
                    "action": {
                        "type": "message",
                        "label": "帳戶間轉帳",
                        "text": "我要轉帳"
                    }
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "button",
                            "style": "link",
                            "height": "sm",
                            "action":{
                                "type": "message",
                                "label": "新增帳戶",
                                "text": "新增銀行帳戶"
                            },
                            "flex": 1
                        },
                        {
                            "type": "button",
                            "style": "link",
                            "height": "sm",
                            "action": {
                                "type": "message",
                                "label": "查看支出",
                                "text": "查詢本月支出"
                            },
                            "flex": 1
                        }
                    ]
                }
            ]
        }

        return FlexSendMessage(
            alt_text=f"資產總覽 ${total_assets:,.0f}",
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
        
    def _is_cold_start(self):
        """檢測是否為冷啟動期間"""
        current_time = time.time()
        startup_duration = current_time - self._startup_time

        #啟動後 30 秒內視為冷啟動期
        if startup_duration < 30:
            print(f"冷啟動檢測: 啟動後 {startup_duration:.1f} 秒")
            return True
        
        #第一次通過 30 秒時，標記為正常運行
        if self._is_warming_up:
            self._is_warming_up = False
            print("系統暖機完成，進入正常運行模式")

        return False

    def _log_system_status(self):
        """紀錄系統狀態"""
        current_time = time.time()
        uptime = current_time - self._startup_time

        status = "暖機中" if self._is_warming_up else "正常運行"
        print(f"系統狀態 {status}, 運行時間: {uptime:.1f} 秒")