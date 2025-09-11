import os
import time
import google.generativeai as genai
from datetime import datetime
from .message_parser import MessageParser
from .handlers import ExpenseHandler, IncomeHandler, QueryHandler, AssetHandler
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, 
    FlexSendMessage
)

class LineBotManager:
    def __init__(self, budget_manager=None, asset_manager=None):

        self._startup_time = time.time()
        self._is_warming_up = True
        #Line Bot設定
        self.line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
        self.handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
        
        # Gemini設定
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('models/gemini-1.5-flash')

        #依賴注入現有 managers
        self.budget_manager = budget_manager
        self.asset_manager = asset_manager
        
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
            cold_start_checker=self._is_cold_start
        )

        # 建立 Handler實例
        self.expense_handler = ExpenseHandler(budget_manager)
        self.income_handler = IncomeHandler(budget_manager)
        self.query_handler = QueryHandler(budget_manager)
        self.asset_handler = AssetHandler(asset_manager)

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
            if self._is_cold_start():
                print(f"檢測到冷啟動，訊息: {user_message}")
                self.reply_message_flex(event.reply_token,
                    "🚀 系統剛啟動完成！\n請重新發送您的訊息，我現在準備好了 😊")
                return

            parsed_data = self.message_parser.parse(user_message)
            response_message = self.process_parsed_message(parsed_data, user_id)
            self.reply_message_flex(event.reply_token, response_message)

        except Exception as e:
            print(f"LINE Bot 錯誤: {e}")
            # 如果是啟動期間的錯誤，可能是資源尚未載入
            error_msg = "系統正在啟動中，請稍後重新發送訊息" if self._is_cold_start() else "抱歉，系統暫時無法處理，請稍後再試"
            self.reply_message_flex(event.reply_token, error_msg)

    def process_parsed_message(self, parsed_data, user_id):
        """處理解析後的訊息"""
        message_type = parsed_data.get("type")

        if message_type == "expense":
            result = self.expense_handler.handle(parsed_data, user_id)
            if result["success"]:
                return self._format_expense_success_flex(result["data"], result.get("budget_status"))
            else:
                return f"紀錄失敗: {result['message']}"
            
        elif message_type == "income":
            result = self.income_handler.handle(parsed_data, user_id)
            if result["success"]:
                return self._format_income_success_flex(result["data"])
            else:
                return f"記錄失敗: {result['message']}"
            
        elif message_type == "query":
            result = self.query_handler.handle(user_id)
            if result["success"]:
                return self._create_monthly_summary_flex(
                    result["month"], 
                    result["total_expenses"], 
                    result["transaction_count"], 
                    result["recent_transactions"], 
                    result["category_stats"]
                )
            else:
                return result["message"]
            
        elif message_type == "asset_query":
            result = self.asset_handler.handle(user_id)
            if result["success"]:
                return self._create_asset_overview_flex(result["totals"])
            else:
                return f"查詢失敗: {result['message']}"
        else:
            return self.get_help_message()
        
    
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
        
    def _format_expense_success_flex(self, data, budget_status=None):
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