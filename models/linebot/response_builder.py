from linebot.models import FlexSendMessage
from .themes import AccountingTheme, StatisticsTheme, OperationTheme

class ResponseBuilder:
    """統一的回應建構器 - 使用主題化設計"""
    
    def __init__(self):
        self.accounting_theme = AccountingTheme()
        self.statistics_theme = StatisticsTheme()
        self.operation_theme = OperationTheme()
    
    # === 記帳相關回應 ===
    def create_expense_success(self, data, budget_status=None):
        """建立支出成功回應"""
        return self.accounting_theme.create_expense_success(data, budget_status)
    
    def create_income_success(self, data):
        """建立收入成功回應"""
        return self.accounting_theme.create_income_success(data)
    
    # === 統計查詢相關回應 ===
    def create_monthly_summary(self, month, total, count, transactions, category_stats):
        """建立月度統計回應"""
        return self.statistics_theme.create_monthly_summary(month, total, count, transactions, category_stats)
    
    def create_asset_overview(self, totals):
        """建立資產總覽回應，支援新版 accounts schema 的多幣別 totals。"""
        currency_totals = {
            currency: data
            for currency, data in totals.items()
            if isinstance(data, dict) and data.get("total", 0) > 0
        }
        primary_currency, primary_total = self._get_primary_currency_total(currency_totals)

        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "資產總覽",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#333333",
                    },
                    {
                        "type": "text",
                        "text": self._format_asset_total(primary_currency, primary_total, currency_totals),
                        "weight": "bold",
                        "size": "3xl",
                        "color": "#4CAF50",
                        "margin": "md",
                    },
                    {
                        "type": "text",
                        "text": "依幣別顯示可追蹤帳戶餘額",
                        "size": "xs",
                        "color": "#999999",
                        "margin": "sm",
                    },
                ],
                "backgroundColor": "#F8F9FA",
                "paddingAll": "20px",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [],
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    self._create_message_button("帳戶間轉帳", "我要轉帳", style="primary", color="#4CAF50"),
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "spacing": "sm",
                        "contents": [
                            self._create_message_button("新增帳戶", "新增銀行帳戶"),
                            self._create_message_button("管理帳戶", "更新餘額"),
                        ],
                    },
                ],
            },
        }

        if currency_totals:
            flex_content["body"]["contents"].append({
                "type": "text",
                "text": "帳戶餘額",
                "weight": "bold",
                "size": "md",
                "color": "#333333",
                "margin": "lg",
            })
            for currency, data in currency_totals.items():
                flex_content["body"]["contents"].append(
                    self._create_currency_asset_section(currency, data)
                )
        else:
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
                        "margin": "sm",
                    },
                    {
                        "type": "text",
                        "text": "點擊下方按鈕開始管理您的帳戶",
                        "size": "sm",
                        "color": "#999999",
                        "align": "center",
                        "margin": "sm",
                    },
                ],
                "margin": "lg",
                "paddingAll": "20px",
            })

        return FlexSendMessage(alt_text="資產總覽", contents=flex_content)

    def _get_primary_currency_total(self, currency_totals):
        if "TWD" in currency_totals:
            return "TWD", currency_totals["TWD"].get("total", 0)
        if currency_totals:
            currency, data = next(iter(currency_totals.items()))
            return currency, data.get("total", 0)
        return None, 0

    def _format_asset_total(self, currency, amount, currency_totals):
        if not currency_totals:
            return "尚無帳戶餘額"
        if len(currency_totals) > 1:
            return "多幣別資產"
        return f"{currency} {amount:,.0f}"

    def _create_currency_asset_section(self, currency, data):
        account_type_labels = {
            "cash": "現金",
            "bank": "銀行",
            "credit_card": "信用卡",
            "e_wallet": "電子錢包",
            "prepaid_card": "儲值卡",
            "external": "外部帳戶",
            "investment": "投資",
            "other": "其他",
        }
        total = data.get("total", 0)
        rows = [
            {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": currency,
                        "weight": "bold",
                        "size": "sm",
                        "color": "#333333",
                        "flex": 1,
                    },
                    {
                        "type": "text",
                        "text": f"{total:,.0f}",
                        "weight": "bold",
                        "size": "sm",
                        "color": "#333333",
                        "align": "end",
                        "flex": 2,
                    },
                ],
            }
        ]

        for account_type, amount in data.get("by_type", {}).items():
            if amount <= 0:
                continue
            rows.append({
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": account_type_labels.get(account_type, account_type),
                        "size": "xs",
                        "color": "#666666",
                        "flex": 1,
                    },
                    {
                        "type": "text",
                        "text": f"{amount:,.0f}",
                        "size": "xs",
                        "color": "#666666",
                        "align": "end",
                        "flex": 2,
                    },
                ],
                "margin": "xs",
            })

        return {
            "type": "box",
            "layout": "vertical",
            "contents": rows,
            "margin": "md",
            "backgroundColor": "#FFFFFF",
            "paddingAll": "12px",
            "cornerRadius": "8px",
            "borderWidth": "1px",
            "borderColor": "#E5E7EB",
        }

    def _create_message_button(self, label, text, style="link", color=None):
        button = {
            "type": "button",
            "style": style,
            "height": "sm",
            "action": {
                "type": "message",
                "label": label,
                "text": text,
            },
            "flex": 1,
        }
        if color:
            button["color"] = color
        return button
    
    # === 目標相關回應 ===
    def create_goal_overview(self, goals, summary):
        """財務目標目前已從 MVP LINE 流程暫停。"""
        return self.create_goal_unavailable()

    def create_goal_management(self, goals):
        """財務目標目前已從 MVP LINE 流程暫停。"""
        return self.create_goal_unavailable()

    def create_goal_progress(self, goals):
        """財務目標目前已從 MVP LINE 流程暫停。"""
        return self.create_goal_unavailable()

    def create_goal_unavailable(self):
        """建立財務目標暫停訊息。"""
        return self.create_error_message(
            "財務目標功能目前暫停，請先使用記帳、帳戶與旅行帳本功能。"
        )
    
    # === 錯誤和幫助訊息 ===
    def create_error_message(self, message):
        """建立錯誤訊息卡片"""
        return self.create_notice_message("發生問題", message, color="#D64545")

    def create_unrecognized_input_message(self):
        """建立不可解析輸入提示。"""
        flex_content = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": "目前看不出這是一筆記錄",
                        "weight": "bold",
                        "size": "md",
                        "color": "#D97706",
                        "wrap": True,
                    },
                    {
                        "type": "text",
                        "text": "請試試：午餐麥當勞 150",
                        "size": "sm",
                        "color": "#475569",
                        "wrap": True,
                    },
                    {
                        "type": "text",
                        "text": "也可以輸入「幫助」查看可用功能。",
                        "size": "xs",
                        "color": "#64748B",
                        "wrap": True,
                    },
                ],
                "paddingAll": "20px",
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    self._create_message_button("查看幫助", "幫助", style="primary", color="#4CAF50")
                ],
            },
        }
        return FlexSendMessage(alt_text="無法解析輸入", contents=flex_content)

    def create_notice_message(self, title, message, color="#4CAF50"):
        """建立通用通知卡片，供舊流程的純文字提示統一轉為 Flex。"""
        flex_content = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": title,
                        "weight": "bold",
                        "size": "md",
                        "color": color,
                        "wrap": True,
                    },
                    {
                        "type": "text",
                        "text": str(message),
                        "size": "sm",
                        "color": "#333333",
                        "wrap": True,
                        "margin": "md",
                    },
                ],
                "paddingAll": "20px",
            },
        }
        return FlexSendMessage(alt_text=title, contents=flex_content)
    
    def create_help_message(self, is_cold_start=False):
        """建立幫助訊息 - 顯示目前 LINE 端可用操作與輸入範例。"""
        command_sections = [
            {
                "title": "建議輸入",
                "examples": [
                    "午餐麥當勞 150 用現金",
                    "晚餐 680 用國泰信用卡",
                    "薪資 50000 存入銀行",
                    "昨天晚餐 150",
                    "咖啡 5 美元 用美金現金",
                ],
            },
            {
                "title": "查詢與操作",
                "examples": [
                    "本月支出",
                    "我的資產",
                    "我要轉帳",
                ],
            },
        ]

        def create_example_section(section):
            return {
                "type": "box",
                "layout": "vertical",
                "spacing": "xs",
                "contents": [
                    {
                        "type": "text",
                        "text": section["title"],
                        "weight": "bold",
                        "size": "sm",
                        "color": "#1F2937",
                    },
                    *[
                        {
                            "type": "text",
                            "text": f"- {example}",
                            "size": "xs",
                            "color": "#475569",
                            "wrap": True,
                        }
                        for example in section["examples"]
                    ],
                ],
            }

        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "LINE 可用功能",
                        "weight": "bold",
                        "size": "xl",
                        "color": "#4CAF50"
                    },
                    {
                        "type": "text",
                        "text": "可點選功能，也可以直接輸入例句",
                        "size": "sm",
                        "color": "#666666",
                        "margin": "sm",
                        "wrap": True,
                    }
                ],
                "backgroundColor": "#F8F9FA",
                "paddingAll": "20px"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {
                        "type": "box",
                        "layout": "vertical",
                        "spacing": "sm",
                        "contents": [create_example_section(section) for section in command_sections],
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "spacing": "xs",
                        "backgroundColor": "#F8FAFC",
                        "cornerRadius": "8px",
                        "paddingAll": "10px",
                        "contents": [
                            {
                                "type": "text",
                                "text": "帳戶連動提示",
                                "weight": "bold",
                                "size": "xs",
                                "color": "#1F2937",
                            },
                            {
                                "type": "text",
                                "text": "若希望 LINE 自動扣款或入帳，請先新增現金、銀行或信用卡帳戶，再輸入「用國泰信用卡」「存入銀行」等帳戶名稱。",
                                "size": "xs",
                                "color": "#475569",
                                "wrap": True,
                            },
                            {
                                "type": "text",
                                "text": "旅行帳本請開啟 Web 使用；LINE 目前用於快速記帳與查詢。",
                                "size": "xs",
                                "color": "#64748B",
                                "wrap": True,
                            },
                        ],
                    },
                    {
                        "type": "separator",
                        "margin": "sm",
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": "常用入口",
                                "weight": "bold",
                                "size": "sm",
                                "color": "#1F2937",
                            },
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "spacing": "sm",
                                "contents": [
                                    {
                                        "type": "button",
                                        "style": "primary",
                                        "height": "sm",
                                        "color": "#4CAF50",
                                        "action": {
                                            "type": "message",
                                            "label": "快速記帳",
                                            "text": "快速記帳"
                                        },
                                        "flex": 1
                                    },
                                    {
                                        "type": "button",
                                        "style": "link",
                                        "height": "sm",
                                        "action": {
                                            "type": "message",
                                            "label": "記錄收入",
                                            "text": "紀錄收入"
                                        },
                                        "flex": 1
                                    }
                                ]
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
                                        "action": {
                                            "type": "message",
                                            "label": "本月支出",
                                            "text": "查詢本月支出"
                                        },
                                        "flex": 1
                                    },
                                    {
                                        "type": "button",
                                        "style": "link",
                                        "height": "sm",
                                        "action": {
                                            "type": "message",
                                            "label": "資產狀況",
                                            "text": "我的資產"
                                        },
                                        "flex": 1
                                    }
                                ]
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
                                        "action": {
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
                                            "label": "帳戶轉帳",
                                            "text": "我要轉帳"
                                        },
                                        "flex": 1
                                    }
                                ]
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
                                        "action": {
                                            "type": "message",
                                            "label": "設定預算",
                                            "text": "設定預算"
                                        },
                                        "flex": 1
                                    },
                                    {
                                        "type": "box",
                                        "layout": "vertical",
                                        "contents": [],
                                        "flex": 1
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }
        
        # 冷啟動提示
        if is_cold_start:
            flex_content["footer"] = {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "提示：系統剛啟動，如無回應請重新發送",
                        "size": "xs",
                        "color": "#FF9800",
                        "wrap": True,
                        "align": "center"
                    }
                ]
            }
        
        return FlexSendMessage(
            alt_text="LINE 可用功能",
            contents=flex_content
        )
