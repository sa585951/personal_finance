from linebot.models import TextSendMessage, FlexSendMessage
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
        """建立資產總覽回應"""
        return self.statistics_theme.create_asset_overview(totals)
    
    # === 目標相關回應 ===
    def create_goal_overview(self, goals, summary):
        """建立財務目標總覽回應"""
        return self.statistics_theme.create_goal_overview(goals, summary)

    def create_goal_management(self, goals):
        """建立財務目標管理回應"""
        return self.statistics_theme.create_goal_management(goals)

    def create_goal_progress(self, goals):
        """建立財務目標進度回應"""
        return self.statistics_theme.create_goal_progress(goals)
    
    # === 錯誤和幫助訊息 ===
    def create_error_message(self, message):
        """建立錯誤訊息"""
        return TextSendMessage(text=f"❌ {message}")
    
    def create_help_message(self, is_cold_start=False):
        """建立幫助訊息 - 使用 Flex Message 按鈕"""
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "個人財務助手",
                        "weight": "bold",
                        "size": "xl",
                        "color": "#4CAF50"
                    },
                    {
                        "type": "text",
                        "text": "選擇您要使用的功能",
                        "size": "md",
                        "color": "#666666",
                        "margin": "sm"
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
                    # 記帳區塊
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": "💰 記帳功能",
                                "weight": "bold",
                                "size": "md",
                                "color": "#333333",
                                "margin": "sm"
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
                            }
                        ]
                    },
                    
                    # 查詢區塊
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": "📊 查詢統計",
                                "weight": "bold",
                                "size": "md",
                                "color": "#333333",
                                "margin": "sm"
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
                            }
                        ]
                    },
                    
                    # 管理區塊
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": "🏦 帳戶管理",
                                "weight": "bold",
                                "size": "md",
                                "color": "#333333",
                                "margin": "sm"
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
                                        "type": "spacer",
                                        "size": "sm",
                                        "flex": 1
                                    }
                                ]
                            }
                        ]
                    },
                    
                    # 目標區塊
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": "🎯 財務目標",
                                "weight": "bold",
                                "size": "md",
                                "color": "#333333",
                                "margin": "sm"
                            },
                            {
                                "type": "button",
                                "style": "link",
                                "height": "sm",
                                "action": {
                                    "type": "message",
                                    "label": "查看目標",
                                    "text": "我的財務目標"
                                }
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
                        "text": "💡 提示：系統剛啟動，如無回應請重新發送",
                        "size": "xs",
                        "color": "#FF9800",
                        "wrap": True,
                        "align": "center"
                    }
                ]
            }
        
        return FlexSendMessage(
            alt_text="歡迎使用個人財務助手",
            contents=flex_content
        )