from .base_theme import BaseTheme
from datetime import datetime
from linebot.models import FlexSendMessage

class StatisticsTheme(BaseTheme):
    """統計主題 - 表格化、數據呈現風格"""
    
    def create_monthly_summary(self, month, total, count, transactions, category_stats):
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
    
    def create_asset_overview(self, totals):
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
                                "label": "管理帳戶",
                                "text": "更新餘額"
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
