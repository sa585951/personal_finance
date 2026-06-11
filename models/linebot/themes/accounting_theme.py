from .base_theme import BaseTheme
from linebot.models import FlexSendMessage

class AccountingTheme(BaseTheme):
    """記帳主題 - 氣泡式、即時反饋風格"""
    
    def create_expense_success(self, data, budget_status=None):
        """建立支出成功訊息 - 模仿小旺來的氣泡風格"""
        category = data.get("category", "其他")
        amount = data.get("amount", 0)
        description = data.get("description") or ""
        account_message = data.get("account_message")
        
        category_color = self.CATEGORY_COLORS.get(category, self.COLORS['text_muted'])
        detail_rows = [
            self._create_info_row("時間", "剛剛"),
        ]
        if description:
            detail_rows.insert(0, self._create_info_row("備註", description))
        if account_message:
            detail_rows.append(self._create_info_row("帳戶", account_message))
        
        flex_content = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    # 分類標籤 (類似小旺來的綠色氣泡)
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": category,
                                "weight": "bold",
                                "color": self.COLORS['text_white'],
                                "size": self.FONT_SIZE['sm']
                            },
                            {
                                "type": "text",
                                "text": "記帳成功",
                                "weight": "bold",
                                "color": self.COLORS['text_white'],
                                "size": self.FONT_SIZE['xs'],
                                "align": "end"
                            }
                        ],
                        "backgroundColor": category_color,
                        "paddingAll": self.SPACING['md'],
                        "cornerRadius": self.BORDER_RADIUS['md']
                    },
                    
                    # 金額顯示 (突出但溫和)
                    {
                        "type": "text",
                        "text": f"${amount:,}",
                        "weight": "bold",
                        "size": self.FONT_SIZE['4xl'],
                        "margin": self.SPACING['lg'],
                        "color": self.COLORS['text_primary']
                    },
                    
                    # 詳細資訊
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": self.SPACING['lg'],
                        "spacing": self.SPACING['sm'],
                        "contents": detail_rows
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": self.SPACING['sm'],
                "contents": [
                    self._create_link_button("查看本月支出", "查詢本月支出"),
                    self._create_link_button("查看資產狀況", "我的資產")
                ]
            }
        }
        
        # 預算狀態提醒
        if budget_status:
            flex_content["body"]["contents"].append({
                "type": "separator",
                "margin": self.SPACING['lg']
            })
            flex_content["body"]["contents"].append({
                "type": "box",
                "layout": "vertical",
                "margin": self.SPACING['lg'],
                "contents": [
                    {
                        "type": "text",
                        "text": budget_status["title"],
                        "size": self.FONT_SIZE['sm'],
                        "color": budget_status["color"],
                        "weight": "bold"
                    },
                    {
                        "type": "text",
                        "text": budget_status["message"],
                        "size": self.FONT_SIZE['xs'],
                        "color": self.COLORS['text_secondary'],
                        "wrap": True,
                        "margin": self.SPACING['xs']
                    }
                ]
            })
        
        return FlexSendMessage(
            alt_text=f"{category} ${amount:,} 記帳成功",
            contents=flex_content
        )
    
    def create_income_success(self, data):
        """建立收入成功訊息"""
        amount = data.get("amount", 0)
        description = data.get("description") or ""
        account_message = data.get("account_message")
        detail_rows = [
            self._create_info_row("時間", "剛剛"),
        ]
        if description:
            detail_rows.insert(0, self._create_info_row("備註", description))
        if account_message:
            detail_rows.append(self._create_info_row("帳戶", account_message))
        
        flex_content = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    # 收入標籤
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": "收入",
                                "weight": "bold",
                                "color": self.COLORS['text_white'],
                                "size": self.FONT_SIZE['sm']
                            },
                            {
                                "type": "text",
                                "text": "記錄成功",
                                "weight": "bold",
                                "color": self.COLORS['text_white'],
                                "size": self.FONT_SIZE['xs'],
                                "align": "end"
                            }
                        ],
                        "backgroundColor": self.COLORS['primary_green'],
                        "paddingAll": self.SPACING['md'],
                        "cornerRadius": self.BORDER_RADIUS['md']
                    },
                    
                    # 收入金額 (加上 + 號)
                    {
                        "type": "text",
                        "text": f"+${amount:,}",
                        "weight": "bold",
                        "size": self.FONT_SIZE['4xl'],
                        "margin": self.SPACING['lg'],
                        "color": self.COLORS['text_success']
                    },
                    
                    # 詳細資訊
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": self.SPACING['lg'],
                        "spacing": self.SPACING['sm'],
                        "contents": detail_rows
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": self.SPACING['sm'],
                "contents": [
                    self._create_link_button("查看本月支出", "查詢本月支出"),
                    self._create_link_button("查看資產狀況", "我的資產")
                ]
            }
        }
        
        return FlexSendMessage(
            alt_text=f"收入 +${amount:,} 記錄成功",
            contents=flex_content
        )
    
    def _create_info_row(self, label, value):
        """建立資訊行"""
        return {
            "type": "box",
            "layout": "baseline",
            "contents": [
                {
                    "type": "text",
                    "text": label,
                    "color": self.COLORS['text_secondary'],
                    "size": self.FONT_SIZE['sm'],
                    "flex": 1
                },
                {
                    "type": "text",
                    "text": str(value),
                    "wrap": True,
                    "color": self.COLORS['text_primary'],
                    "size": self.FONT_SIZE['sm'],
                    "flex": 3
                }
            ]
        }
    
    def _create_link_button(self, label, action_text):
        """建立連結按鈕"""
        return {
            "type": "button",
            "style": "link",
            "height": "sm",
            "action": {
                "type": "message",
                "label": label,
                "text": action_text
            }
        }
