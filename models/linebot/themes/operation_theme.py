from datetime import datetime
from .base_theme import BaseTheme
from linebot.models import FlexSendMessage

class OperationTheme(BaseTheme):
    """操作主題 - 步驟化、引導式風格"""
    # ====== Add Account ======
    def create_add_account_confirmation(self, data, balance):
        """建立新增帳戶確認 Flex Message"""
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "確認新增帳戶",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#333333"
                    }
                ],
                "backgroundColor": "#E3F2FD",
                "paddingAll": "16px"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "baseline",
                        "contents": [
                            {"type": "text", "text": "銀行名稱", "size": "sm", "color": "#666666", "flex": 2},
                            {"type": "text", "text": data['bank_name'], "size": "sm", "color": "#333333", "flex": 3, "wrap": True, "weight": "bold"}
                        ],
                        "margin": "lg"
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "contents": [
                            {"type": "text", "text": "帳戶類型", "size": "sm", "color": "#666666", "flex": 2},
                            {"type": "text", "text": data['account_type'], "size": "sm", "color": "#333333", "flex": 3, "wrap": True, "weight": "bold"}
                        ],
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "contents": [
                            {"type": "text", "text": "初始餘額", "size": "sm", "color": "#666666", "flex": 2},
                            {"type": "text", "text": f"${balance:,.0f}", "size": "sm", "color": "#4CAF50", "flex": 3, "weight": "bold"}
                        ],
                        "margin": "md"
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "style": "secondary",
                        "height": "sm",
                        "action": {
                            "type": "message",
                            "label": "取消",
                            "text": "取消操作"
                        },
                        "flex": 1
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "height": "sm",
                        "color": "#4CAF50",
                        "action": {
                            "type": "message",
                            "label": "確認新增",
                            "text": "確認新增"
                        },
                        "flex": 1
                    }
                ]
            }
        }
        
        return FlexSendMessage(
            alt_text=f"確認新增 {data['bank_name']} {data['account_type']}",
            contents=flex_content
        )

    def create_bank_name_input(self, error_message=None):
        """建立銀行名稱輸入 Flex Message"""
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "新增銀行帳戶",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#333333"
                    },
                    {
                        "type": "text",
                        "text": "步驟 1/3",
                        "size": "sm",
                        "color": "#666666",
                        "margin": "sm"
                    }
                ],
                "backgroundColor": "#E8F5E8",
                "paddingAll": "16px"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "請輸入銀行名稱",
                        "weight": "bold",
                        "size": "md",
                        "color": "#333333",
                        "margin": "lg"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": "💡 範例：",
                                "size": "sm",
                                "color": "#666666",
                                "margin": "md"
                            },
                            {
                                "type": "text",
                                "text": "• 玉山銀行",
                                "size": "sm",
                                "color": "#666666",
                                "margin": "xs"
                            },
                            {
                                "type": "text",
                                "text": "• 台灣銀行",
                                "size": "sm",
                                "color": "#666666",
                                "margin": "xs"
                            },
                            {
                                "type": "text",
                                "text": "• 中國信託",
                                "size": "sm",
                                "color": "#666666",
                                "margin": "xs"
                            }
                        ]
                    }
                ]
            }
        }
        
        # 如果有錯誤訊息，加入警告區塊
        if error_message:
            flex_content["body"]["contents"].insert(0, {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "⚠️ " + error_message,
                        "size": "sm",
                        "color": "#F44336",
                        "weight": "bold",
                        "wrap": True
                    }
                ],
                "backgroundColor": "#FFEBEE",
                "paddingAll": "12px",
                "cornerRadius": "8px"
            })
        
        # 取消按鈕
        flex_content["footer"] = {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "action": {
                        "type": "message",
                        "label": "取消新增",
                        "text": "取消操作"
                    }
                }
            ]
        }
        
        return FlexSendMessage(
            alt_text="請輸入銀行名稱",
            contents=flex_content
        )
    
    def create_balance_input_flex(self, error_message=None):
        """建立餘額輸入 Flex Message"""
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "新增銀行帳戶",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#333333"
                    },
                    {
                        "type": "text",
                        "text": "步驟 3/3",
                        "size": "sm",
                        "color": "#666666",
                        "margin": "sm"
                    }
                ],
                "backgroundColor": "#E8F5E8",
                "paddingAll": "16px"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "請輸入帳戶初始餘額",
                        "weight": "bold",
                        "size": "md",
                        "color": "#333333",
                        "margin": "lg"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": "💡 範例：50000",
                                "size": "sm",
                                "color": "#666666",
                                "margin": "md"
                            },
                            {
                                "type": "text",
                                "text": "⚠️ 注意：金額不能為負數",
                                "size": "sm",
                                "color": "#FF9800",
                                "margin": "sm"
                            }
                        ]
                    }
                ]
            }
        }
        
        # 如果有錯誤訊息，加入警告區塊
        if error_message:
            flex_content["body"]["contents"].insert(0, {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "⚠️ " + error_message,
                        "size": "sm",
                        "color": "#F44336",
                        "weight": "bold",
                        "wrap": True
                    }
                ],
                "backgroundColor": "#FFEBEE",
                "paddingAll": "12px",
                "cornerRadius": "8px"
            })
        
        # 取消按鈕
        flex_content["footer"] = {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "action": {
                        "type": "message",
                        "label": "取消新增",
                        "text": "取消操作"
                    }
                }
            ]
        }
        
        return FlexSendMessage(
            alt_text="請輸入帳戶餘額",
            contents=flex_content
        )
    
    def create_account_type_selection_flex(self, account_types):
        """建立帳戶類型選擇 Flex Message"""
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "選擇帳戶類型",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#333333"
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
        
        # 帳戶類型顏色對應
        type_colors = {
            "活存": "#4CAF50",
            "定存": "#2196F3", 
            "投資": "#FF9800",
            "其他": "#9E9E9E"
        }
        
        # 新增帳戶類型選項
        for account_type in account_types:
            color = type_colors.get(account_type, "#9E9E9E")
            type_button = {
                "type": "button",
                "style": "link",
                "height": "sm",
                "action": {
                    "type": "message",
                    "label": account_type,
                    "text": f"選擇類型:{account_type}"
                },
                "color": color,
                "margin": "sm"
            }
            flex_content["body"]["contents"].append(type_button)
        
        # 取消按鈕
        flex_content["body"]["contents"].append({
            "type": "button",
            "style": "secondary",
            "height": "sm",
            "action": {
                "type": "message",
                "label": "取消",
                "text": "取消操作"
            },
            "margin": "lg"
        })
        
        return FlexSendMessage(
            alt_text="選擇帳戶類型",
            contents=flex_content
        )
    
    def create_add_account_success_flex(self, data):
        """建立新增帳戶成功 Flex Message"""
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "帳戶新增成功",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#FFFFFF"
                    },
                    {
                        "type": "text",
                        "text": f"${data['balance']:,.0f}",
                        "weight": "bold",
                        "size": "3xl",
                        "color": "#FFFFFF",
                        "margin": "md"
                    }
                ],
                "backgroundColor": "#4CAF50",
                "paddingAll": "16px"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "baseline",
                        "contents": [
                            {"type": "text", "text": "銀行", "size": "sm", "color": "#666666", "flex": 1},
                            {"type": "text", "text": data['bank_name'], "size": "sm", "color": "#333333", "flex": 3, "wrap": True, "weight": "bold"}
                        ],
                        "margin": "lg"
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "contents": [
                            {"type": "text", "text": "類型", "size": "sm", "color": "#666666", "flex": 1},
                            {"type": "text", "text": data['account_type'], "size": "sm", "color": "#333333", "flex": 3, "weight": "bold"}
                        ],
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "contents": [
                            {"type": "text", "text": "時間", "size": "sm", "color": "#666666", "flex": 1},
                            {"type": "text", "text": datetime.now().strftime("%Y/%m/%d %H:%M"), "size": "sm", "color": "#333333", "flex": 3}
                        ],
                        "margin": "md"
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
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
            alt_text=f"成功新增 {data['bank_name']} {data['account_type']}",
            contents=flex_content
        )
    
    def create_transfer_account_selection(self, assets, title, selection_type):
        """建立帳戶選擇 Flex Message"""
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": title,
                        "weight": "bold",
                        "size": "lg",
                        "color": "#333333"
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
        
        # 新增帳戶選項
        for account_key, account in assets.items():
            account_button = {
                "type": "button",
                "style": "link",
                "height": "sm",
                "action": {
                    "type": "message",
                    "label": f"{account['bank_name']} {account['account_type']} (${account['balance']:,.0f})",
                    "text": f"選擇帳戶:{account_key}"
                },
                "margin": "sm"
            }
            flex_content["body"]["contents"].append(account_button)
        
        # 取消按鈕
        flex_content["body"]["contents"].append({
            "type": "button",
            "style": "secondary",
            "height": "sm",
            "action": {
                "type": "message",
                "label": "取消",
                "text": "取消操作"
            },
            "margin": "lg"
        })
        
        return FlexSendMessage(
            alt_text=title,
            contents=flex_content
        )
    
    # ====== Transfer ======    
    def create_transfer_confirmation(self, data, amount):
        """建立轉帳確認 Flex Message"""
        assets = self.asset_manager.get_all_assets()
        source_account = assets[data['source_account']]
        target_account = assets[data['target_account']]
        
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "確認轉帳",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#333333"
                    },
                    {
                        "type": "text",
                        "text": f"${amount:,.0f}",
                        "weight": "bold",
                        "size": "3xl",
                        "color": "#FF9800",
                        "margin": "md"
                    }
                ],
                "backgroundColor": "#FFF3E0",
                "paddingAll": "16px"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "baseline",
                        "contents": [
                            {"type": "text", "text": "轉出帳戶", "size": "sm", "color": "#666666", "flex": 2},
                            {"type": "text", "text": f"{source_account['bank_name']} {source_account['account_type']}", "size": "sm", "color": "#333333", "flex": 3, "wrap": True}
                        ],
                        "margin": "lg"
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "contents": [
                            {"type": "text", "text": "轉入帳戶", "size": "sm", "color": "#666666", "flex": 2},
                            {"type": "text", "text": f"{target_account['bank_name']} {target_account['account_type']}", "size": "sm", "color": "#333333", "flex": 3, "wrap": True}
                        ],
                        "margin": "md"
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "style": "secondary",
                        "height": "sm",
                        "action": {
                            "type": "message",
                            "label": "取消",
                            "text": "取消轉帳"
                        },
                        "flex": 1
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "height": "sm",
                        "color": "#4CAF50",
                        "action": {
                            "type": "message",
                            "label": "確認轉帳",
                            "text": "確認轉帳"
                        },
                        "flex": 1
                    }
                ]
            }
        }
        
        return FlexSendMessage(
            alt_text=f"確認轉帳 ${amount:,.0f}",
            contents=flex_content
        )
    
    def create_transfer_success(self, data):
        """建立轉帳成功 Flex Message"""
        assets = self.asset_manager.get_all_assets()
        source_account = assets[data['source_account']]
        target_account = assets[data['target_account']]
        amount = data['amount']
        
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "轉帳成功",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#FFFFFF"
                    },
                    {
                        "type": "text",
                        "text": f"${amount:,.0f}",
                        "weight": "bold",
                        "size": "3xl",
                        "color": "#FFFFFF",
                        "margin": "md"
                    }
                ],
                "backgroundColor": "#4CAF50",
                "paddingAll": "16px"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "baseline",
                        "contents": [
                            {"type": "text", "text": "轉出", "size": "sm", "color": "#666666", "flex": 1},
                            {"type": "text", "text": f"{source_account['bank_name']} {source_account['account_type']}", "size": "sm", "color": "#333333", "flex": 3, "wrap": True}
                        ],
                        "margin": "lg"
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "contents": [
                            {"type": "text", "text": "轉入", "size": "sm", "color": "#666666", "flex": 1},
                            {"type": "text", "text": f"{target_account['bank_name']} {target_account['account_type']}", "size": "sm", "color": "#333333", "flex": 3, "wrap": True}
                        ],
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "contents": [
                            {"type": "text", "text": "時間", "size": "sm", "color": "#666666", "flex": 1},
                            {"type": "text", "text": datetime.now().strftime("%Y/%m/%d %H:%M"), "size": "sm", "color": "#333333", "flex": 3}
                        ],
                        "margin": "md"
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
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
            alt_text=f"轉帳成功 ${amount:,.0f}",
            contents=flex_content
        )
    
    # ===== Update 資產 ======
    def create_update_balance_account_selection(self, assets, error_message=None):
        """建立帳戶選擇 Flex Message"""
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "更新帳戶餘額",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#333333"
                    },
                    {
                        "type": "text",
                        "text": "步驟 1/3 - 選擇帳戶",
                        "size": "sm",
                        "color": "#666666",
                        "margin": "sm"
                    }
                ],
                "backgroundColor": "#E3F2FD",
                "paddingAll": "16px"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": []
            }
        }
        
        # 錯誤訊息
        if error_message:
            flex_content["body"]["contents"].append({
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "⚠️ " + error_message,
                        "size": "sm",
                        "color": "#F44336",
                        "weight": "bold",
                        "wrap": True
                    }
                ],
                "backgroundColor": "#FFEBEE",
                "paddingAll": "12px",
                "cornerRadius": "8px",
                "margin": "md"
            })
        
        # 帳戶列表
        for asset in assets:
            account_key = asset['account_key']
            account_button = {
                "type": "button",
                "style": "link",
                "height": "sm",
                "action": {
                    "type": "message",
                    "label": f"{asset['bank_name']} {asset['account_type']} (${asset['balance']:,.0f})",
                    "text": f"選擇帳戶:{account_key}"
                },
                "margin": "sm"
            }
            flex_content["body"]["contents"].append(account_button)
        
        # 取消按鈕
        flex_content["body"]["contents"].append({
            "type": "button",
            "style": "secondary",
            "height": "sm",
            "action": {
                "type": "message",
                "label": "取消操作",
                "text": "取消操作"
            },
            "margin": "lg"
        })
        
        return FlexSendMessage(
            alt_text="選擇要更新的帳戶",
            contents=flex_content
        )
    
    def create_balance_input(self, asset, error_message=None):
        """建立餘額輸入 Flex Message"""
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "更新帳戶餘額",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#333333"
                    },
                    {
                        "type": "text",
                        "text": "步驟 2/3 - 輸入新餘額",
                        "size": "sm",
                        "color": "#666666",
                        "margin": "sm"
                    }
                ],
                "backgroundColor": "#E3F2FD",
                "paddingAll": "16px"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"帳戶：{asset['bank_name']} {asset['account_type']}",
                                "weight": "bold",
                                "size": "md",
                                "color": "#333333"
                            },
                            {
                                "type": "text",
                                "text": f"目前餘額：${asset['balance']:,.0f}",
                                "size": "sm",
                                "color": "#666666",
                                "margin": "sm"
                            }
                        ],
                        "backgroundColor": "#F5F5F5",
                        "paddingAll": "12px",
                        "cornerRadius": "8px",
                        "margin": "md"
                    },
                    {
                        "type": "text",
                        "text": "請輸入新的餘額金額：",
                        "weight": "bold",
                        "size": "md",
                        "color": "#333333",
                        "margin": "lg"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": "💡 範例：150000",
                                "size": "sm",
                                "color": "#666666"
                            }
                        ],
                        "margin": "sm"
                    }
                ]
            }
        }
        
        # 錯誤訊息
        if error_message:
            flex_content["body"]["contents"].insert(-2, {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "⚠️ " + error_message,
                        "size": "sm",
                        "color": "#F44336",
                        "weight": "bold",
                        "wrap": True
                    }
                ],
                "backgroundColor": "#FFEBEE",
                "paddingAll": "12px",
                "cornerRadius": "8px",
                "margin": "md"
            })
        
        # 取消按鈕
        flex_content["footer"] = {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "action": {
                        "type": "message",
                        "label": "取消更新",
                        "text": "取消操作"
                    }
                }
            ]
        }
        
        return FlexSendMessage(
            alt_text="請輸入新的餘額金額",
            contents=flex_content
        )
    
    def create_update_confirmation(self, data, new_balance):
        """建立更新確認 Flex Message"""
        asset = data['selected_asset']
        old_balance = asset['balance']
        difference = new_balance - old_balance
        
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "確認更新餘額",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#333333"
                    },
                    {
                        "type": "text",
                        "text": "步驟 3/3 - 確認更新",
                        "size": "sm",
                        "color": "#666666",
                        "margin": "sm"
                    }
                ],
                "backgroundColor": "#E8F5E8",
                "paddingAll": "16px"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "baseline",
                        "contents": [
                            {"type": "text", "text": "帳戶", "size": "sm", "color": "#666666", "flex": 2},
                            {"type": "text", "text": f"{asset['bank_name']} {asset['account_type']}", "size": "sm", "color": "#333333", "flex": 3, "wrap": True, "weight": "bold"}
                        ],
                        "margin": "lg"
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "contents": [
                            {"type": "text", "text": "目前餘額", "size": "sm", "color": "#666666", "flex": 2},
                            {"type": "text", "text": f"${old_balance:,.0f}", "size": "sm", "color": "#333333", "flex": 3, "weight": "bold"}
                        ],
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "contents": [
                            {"type": "text", "text": "新餘額", "size": "sm", "color": "#666666", "flex": 2},
                            {"type": "text", "text": f"${new_balance:,.0f}", "size": "sm", "color": "#4CAF50", "flex": 3, "weight": "bold"}
                        ],
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "contents": [
                            {"type": "text", "text": "變動", "size": "sm", "color": "#666666", "flex": 2},
                            {"type": "text", "text": f"{'+'if difference >= 0 else ''}{difference:,.0f}", "size": "sm", "color": "#4CAF50" if difference >= 0 else "#F44336", "flex": 3, "weight": "bold"}
                        ],
                        "margin": "md"
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "style": "secondary",
                        "height": "sm",
                        "action": {
                            "type": "message",
                            "label": "取消",
                            "text": "取消更新"
                        },
                        "flex": 1
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "height": "sm",
                        "color": "#4CAF50",
                        "action": {
                            "type": "message",
                            "label": "確認更新",
                            "text": "確認更新"
                        },
                        "flex": 1
                    }
                ]
            }
        }
        
        return FlexSendMessage(
            alt_text=f"確認更新 {asset['bank_name']} {asset['account_type']} 餘額",
            contents=flex_content
        )
    
    def create_update_success(self, data):
        """建立更新成功 Flex Message"""
        asset = data['selected_asset']
        old_balance = asset['balance']
        new_balance = data['new_balance']
        difference = new_balance - old_balance
        
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "餘額更新成功",
                        "weight": "bold",
                        "size": "lg",
                        "color": "#FFFFFF"
                    },
                    {
                        "type": "text",
                        "text": f"${new_balance:,.0f}",
                        "weight": "bold",
                        "size": "3xl",
                        "color": "#FFFFFF",
                        "margin": "md"
                    }
                ],
                "backgroundColor": "#4CAF50",
                "paddingAll": "16px"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "baseline",
                        "contents": [
                            {"type": "text", "text": "帳戶", "size": "sm", "color": "#666666", "flex": 1},
                            {"type": "text", "text": f"{asset['bank_name']} {asset['account_type']}", "size": "sm", "color": "#333333", "flex": 3, "wrap": True, "weight": "bold"}
                        ],
                        "margin": "lg"
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "contents": [
                            {"type": "text", "text": "變動", "size": "sm", "color": "#666666", "flex": 1},
                            {"type": "text", "text": f"{'+'if difference >= 0 else ''}{difference:,.0f}", "size": "sm", "color": "#4CAF50" if difference >= 0 else "#F44336", "flex": 3, "weight": "bold"}
                        ],
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "contents": [
                            {"type": "text", "text": "時間", "size": "sm", "color": "#666666", "flex": 1},
                            {"type": "text", "text": datetime.now().strftime("%Y/%m/%d %H:%M"), "size": "sm", "color": "#333333", "flex": 3}
                        ],
                        "margin": "md"
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
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
            alt_text=f"成功更新 {asset['bank_name']} {asset['account_type']} 餘額",
            contents=flex_content
        )
    
    #====== Delete 資產 ======
    # 在 themes/operation_theme.py 中新增這些方法

    def create_delete_asset_account_selection(self, assets_list, error_message=None):
        """建立刪除資產帳戶選擇 Flex Message"""
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "刪除銀行帳戶",
                        "weight": "bold",
                        "size": self.FONT_SIZE['lg'],
                        "color": self.COLORS['text_primary']
                    },
                    {
                        "type": "text",
                        "text": "步驟 1/2 - 選擇帳戶",
                        "size": self.FONT_SIZE['sm'],
                        "color": self.COLORS['text_secondary'],
                        "margin": self.SPACING['sm']
                    }
                ],
                "backgroundColor": self.COLORS['bg_warning'],  # 使用警告色
                "paddingAll": self.SPACING['lg']
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "⚠️ 注意：只能刪除餘額為 0 的帳戶",
                        "size": self.FONT_SIZE['sm'],
                        "color": self.COLORS['text_error'],
                        "weight": "bold",
                        "wrap": True,
                        "margin": self.SPACING['md']
                    }
                ]
            }
        }
        
        # 錯誤訊息
        if error_message:
            flex_content["body"]["contents"].append(self._create_error_box(error_message))
        
        # 帳戶列表
        for asset in assets_list:
            account_key = asset['account_key']
            balance = asset['balance']
            
            # 根據餘額決定按鈕樣式
            if balance == 0:
                button_style = "primary"
                button_color = self.COLORS['text_error']
                button_text = f"刪除 {asset['bank_name']} {asset['account_type']}"
                action_text = f"刪除帳戶:{account_key}"
            else:
                button_style = "secondary"
                button_color = None
                button_text = f"{asset['bank_name']} {asset['account_type']} (餘額: ${balance:,.0f})"
                action_text = "無法刪除"
            
            account_button = {
                "type": "button",
                "style": button_style,
                "height": "sm",
                "action": {
                    "type": "message",
                    "label": button_text,
                    "text": action_text
                },
                "margin": self.SPACING['sm']
            }
            
            if button_color:
                account_button["color"] = button_color
                
            flex_content["body"]["contents"].append(account_button)
        
        # 取消按鈕
        flex_content["body"]["contents"].append({
            "type": "button",
            "style": "secondary",
            "height": "sm",
            "action": {
                "type": "message",
                "label": "取消操作",
                "text": "取消操作"
            },
            "margin": self.SPACING['lg']
        })
        
        return FlexSendMessage(
            alt_text="選擇要刪除的帳戶",
            contents=flex_content
        )

    def create_delete_asset_confirmation(self, asset):
        """建立刪除資產確認 Flex Message"""
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "⚠️ 確認刪除帳戶",
                        "weight": "bold",
                        "size": self.FONT_SIZE['lg'],
                        "color": self.COLORS['text_white']
                    },
                    {
                        "type": "text",
                        "text": "步驟 2/2 - 最終確認",
                        "size": self.FONT_SIZE['sm'],
                        "color": self.COLORS['text_white'],
                        "margin": self.SPACING['sm']
                    }
                ],
                "backgroundColor": self.COLORS['text_error'],
                "paddingAll": self.SPACING['lg']
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "您即將刪除以下帳戶：",
                        "weight": "bold",
                        "size": self.FONT_SIZE['md'],
                        "color": self.COLORS['text_primary'],
                        "margin": self.SPACING['md']
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            self._create_info_row("銀行", asset['bank_name']),
                            self._create_info_row("類型", asset['account_type']),
                            self._create_info_row("餘額", f"${asset['balance']:,.0f}")
                        ],
                        "backgroundColor": self.COLORS['bg_card'],
                        "paddingAll": self.SPACING['md'],
                        "cornerRadius": self.BORDER_RADIUS['md'],
                        "margin": self.SPACING['md']
                    },
                    {
                        "type": "text",
                        "text": "⚠️ 此操作無法復原，請謹慎考慮！",
                        "size": self.FONT_SIZE['sm'],
                        "color": self.COLORS['text_error'],
                        "weight": "bold",
                        "wrap": True,
                        "margin": self.SPACING['lg']
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "spacing": self.SPACING['sm'],
                "contents": [
                    {
                        "type": "button",
                        "style": "secondary",
                        "height": "sm",
                        "action": {
                            "type": "message",
                            "label": "取消",
                            "text": "取消操作"
                        },
                        "flex": 1
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "height": "sm",
                        "color": self.COLORS['text_error'],
                        "action": {
                            "type": "message",
                            "label": "確認刪除",
                            "text": "確認刪除"
                        },
                        "flex": 1
                    }
                ]
            }
        }
        
        return FlexSendMessage(
            alt_text=f"確認刪除 {asset['bank_name']} {asset['account_type']}",
            contents=flex_content
        )

    def create_delete_asset_success(self, asset):
        """建立刪除資產成功 Flex Message"""
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "帳戶刪除成功",
                        "weight": "bold",
                        "size": self.FONT_SIZE['lg'],
                        "color": self.COLORS['text_white']
                    },
                    {
                        "type": "text",
                        "text": "✅ 操作完成",
                        "size": self.FONT_SIZE['md'],
                        "color": self.COLORS['text_white'],
                        "margin": self.SPACING['md']
                    }
                ],
                "backgroundColor": self.COLORS['text_success'],
                "paddingAll": self.SPACING['lg']
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "已成功刪除以下帳戶：",
                        "size": self.FONT_SIZE['md'],
                        "color": self.COLORS['text_primary'],
                        "margin": self.SPACING['md']
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            self._create_info_row("銀行", asset['bank_name']),
                            self._create_info_row("類型", asset['account_type']),
                            self._create_info_row("時間", datetime.now().strftime("%Y/%m/%d %H:%M"))
                        ],
                        "backgroundColor": self.COLORS['bg_success'],
                        "paddingAll": self.SPACING['md'],
                        "cornerRadius": self.BORDER_RADIUS['md'],
                        "margin": self.SPACING['md']
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
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
            alt_text=f"成功刪除 {asset['bank_name']} {asset['account_type']}",
            contents=flex_content
        )

    # ======  刪除資產 ======

    def create_delete_transaction_selection(self, transactions, error_message=None):
        """建立刪除交易選擇 Flex Message"""
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "刪除交易記錄",
                        "weight": "bold",
                        "size": self.FONT_SIZE['lg'],
                        "color": self.COLORS['text_primary']
                    },
                    {
                        "type": "text",
                        "text": "步驟 1/2 - 選擇交易",
                        "size": self.FONT_SIZE['sm'],
                        "color": self.COLORS['text_secondary'],
                        "margin": self.SPACING['sm']
                    }
                ],
                "backgroundColor": self.COLORS['bg_warning'],
                "paddingAll": self.SPACING['lg']
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "最近 20 筆交易記錄",
                        "weight": "bold",
                        "size": self.FONT_SIZE['md'],
                        "color": self.COLORS['text_primary'],
                        "margin": self.SPACING['md']
                    }
                ]
            }
        }
        
        # 錯誤訊息
        if error_message:
            flex_content["body"]["contents"].append(self._create_error_box(error_message))
        
        # 交易列表表頭
        flex_content["body"]["contents"].append({
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {"type": "text", "text": "日期", "size": self.FONT_SIZE['xs'], "color": self.COLORS['text_muted'], "flex": 1},
                {"type": "text", "text": "類別", "size": self.FONT_SIZE['xs'], "color": self.COLORS['text_muted'], "flex": 2},
                {"type": "text", "text": "金額", "size": self.FONT_SIZE['xs'], "color": self.COLORS['text_muted'], "align": "end", "flex": 1}
            ],
            "margin": self.SPACING['md']
        })
        
        # 交易列表
        for transaction in transactions:
            transaction_id = str(transaction['id'])
            date = transaction.get('date', 'N/A')
            date_str = str(date)[-5:] if date != 'N/A' else 'N/A'
            category = transaction.get('budget_category', 'N/A')
            amount = transaction.get('amount', 0)
            transaction_type = transaction.get('type', 'expense')
            
            # 根據交易類型設定顏色
            amount_color = self.COLORS['text_success'] if transaction_type == 'income' else self.COLORS['text_error']
            amount_text = f"+${amount:,}" if transaction_type == 'income' else f"-${amount:,}"
            
            transaction_button = {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": date_str,
                        "size": self.FONT_SIZE['sm'],
                        "color": self.COLORS['text_primary'],
                        "flex": 1
                    },
                    {
                        "type": "text",
                        "text": category,
                        "size": self.FONT_SIZE['sm'],
                        "color": self.COLORS['text_primary'],
                        "flex": 2,
                        "wrap": True
                    },
                    {
                        "type": "text",
                        "text": amount_text,
                        "size": self.FONT_SIZE['sm'],
                        "color": amount_color,
                        "align": "end",
                        "flex": 1,
                        "weight": "bold"
                    }
                ],
                "margin": self.SPACING['sm'],
                "backgroundColor": self.COLORS['bg_card'],
                "paddingAll": self.SPACING['sm'],
                "cornerRadius": self.BORDER_RADIUS['sm'],
                "action": {
                    "type": "message",
                    "text": f"選擇刪除交易: {category} ({transaction_id})"
                }
            }
            
            flex_content["body"]["contents"].append(transaction_button)
        
        # 取消按鈕
        flex_content["body"]["contents"].append({
            "type": "button",
            "style": "secondary",
            "height": "sm",
            "action": {
                "type": "message",
                "label": "取消操作",
                "text": "取消操作"
            },
            "margin": self.SPACING['lg']
        })
        
        return FlexSendMessage(
            alt_text="選擇要刪除的交易",
            contents=flex_content
        )

    def create_delete_transaction_confirmation(self, transaction):
        """建立刪除交易確認 Flex Message"""
        date = transaction.get('date', 'N/A')
        category = transaction.get('budget_category', 'N/A')
        amount = transaction.get('amount', 0)
        transaction_type = transaction.get('type', 'expense')
        description = transaction.get('description', '')
        
        # 根據交易類型設定樣式
        type_text = "收入" if transaction_type == 'income' else "支出"
        type_color = self.COLORS['text_success'] if transaction_type == 'income' else self.COLORS['text_error']
        amount_text = f"+${amount:,}" if transaction_type == 'income' else f"-${amount:,}"
        
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "⚠️ 確認刪除交易",
                        "weight": "bold",
                        "size": self.FONT_SIZE['lg'],
                        "color": self.COLORS['text_white']
                    },
                    {
                        "type": "text",
                        "text": "步驟 2/2 - 最終確認",
                        "size": self.FONT_SIZE['sm'],
                        "color": self.COLORS['text_white'],
                        "margin": self.SPACING['sm']
                    }
                ],
                "backgroundColor": self.COLORS['text_error'],
                "paddingAll": self.SPACING['lg']
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "您即將刪除以下交易：",
                        "weight": "bold",
                        "size": self.FONT_SIZE['md'],
                        "color": self.COLORS['text_primary'],
                        "margin": self.SPACING['md']
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            self._create_info_row("類型", type_text, type_color),
                            self._create_info_row("日期", str(date)),
                            self._create_info_row("分類", category),
                            self._create_info_row("金額", amount_text, type_color),
                            self._create_info_row("備註", description if description else "無")
                        ],
                        "backgroundColor": self.COLORS['bg_card'],
                        "paddingAll": self.SPACING['md'],
                        "cornerRadius": self.BORDER_RADIUS['md'],
                        "margin": self.SPACING['md']
                    },
                    {
                        "type": "text",
                        "text": "⚠️ 此操作無法復原，請謹慎考慮！",
                        "size": self.FONT_SIZE['sm'],
                        "color": self.COLORS['text_error'],
                        "weight": "bold",
                        "wrap": True,
                        "margin": self.SPACING['lg']
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "spacing": self.SPACING['sm'],
                "contents": [
                    {
                        "type": "button",
                        "style": "secondary",
                        "height": "sm",
                        "action": {
                            "type": "message",
                            "label": "取消",
                            "text": "取消操作"
                        },
                        "flex": 1
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "height": "sm",
                        "color": self.COLORS['text_error'],
                        "action": {
                            "type": "message",
                            "label": "確認刪除",
                            "text": "確認刪除"
                        },
                        "flex": 1
                    }
                ]
            }
        }
        
        return FlexSendMessage(
            alt_text=f"確認刪除{type_text} ${amount:,}",
            contents=flex_content
        )

    def create_delete_transaction_success(self, transaction):
        """建立刪除交易成功 Flex Message"""
        date = transaction.get('date', 'N/A')
        category = transaction.get('budget_category', 'N/A')
        amount = transaction.get('amount', 0)
        transaction_type = transaction.get('type', 'expense')
        
        type_text = "收入" if transaction_type == 'income' else "支出"
        type_color = self.COLORS['text_success'] if transaction_type == 'income' else self.COLORS['text_error']
        amount_text = f"+${amount:,}" if transaction_type == 'income' else f"-${amount:,}"
        
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "交易刪除成功",
                        "weight": "bold",
                        "size": self.FONT_SIZE['lg'],
                        "color": self.COLORS['text_white']
                    },
                    {
                        "type": "text",
                        "text": "✅ 操作完成",
                        "size": self.FONT_SIZE['md'],
                        "color": self.COLORS['text_white'],
                        "margin": self.SPACING['md']
                    }
                ],
                "backgroundColor": self.COLORS['text_success'],
                "paddingAll": self.SPACING['lg']
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "已成功刪除以下交易：",
                        "size": self.FONT_SIZE['md'],
                        "color": self.COLORS['text_primary'],
                        "margin": self.SPACING['md']
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            self._create_info_row("類型", type_text, type_color),
                            self._create_info_row("日期", str(date)),
                            self._create_info_row("分類", category),
                            self._create_info_row("金額", amount_text, type_color),
                            self._create_info_row("刪除時間", datetime.now().strftime("%Y/%m/%d %H:%M"))
                        ],
                        "backgroundColor": self.COLORS['bg_success'],
                        "paddingAll": self.SPACING['md'],
                        "cornerRadius": self.BORDER_RADIUS['md'],
                        "margin": self.SPACING['md']
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
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
                    }
                ]
            }
        }
        
        return FlexSendMessage(
            alt_text=f"成功刪除{type_text} ${amount:,}",
            contents=flex_content
        )

    # 修正 _create_info_row 方法，支援自定義顏色
    def _create_info_row(self, label, value, value_color=None):
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
                    "flex": 2
                },
                {
                    "type": "text",
                    "text": str(value),
                    "wrap": True,
                    "color": value_color or self.COLORS['text_primary'],
                    "size": self.FONT_SIZE['sm'],
                    "flex": 3,
                    "weight": "bold" if value_color else "regular"
                }
            ],
            "margin": self.SPACING['sm']
        }

    # ====== 新增交易流程相關方法 ======

    def create_category_selection(self, categories, transaction_type, error_message=None):
        """建立類別選擇 Flex Message"""
        title = f"新增{transaction_type.capitalize()}"
        alt_text = f"選擇{transaction_type.capitalize()}類別"
        
        buttons = []
        for category in categories:
            buttons.append({
                "type": "button",
                "style": "link",
                "height": "sm",
                "action": {
                    "type": "message",
                    "label": category,
                    "text": f"選擇類別:{category}"
                }
            })

        flex_content = self._create_step_bubble(
            title=title,
            step_text="步驟 1/3 - 選擇類別",
            body_contents=buttons,
            error_message=error_message
        )
        
        return FlexSendMessage(alt_text=alt_text, contents=flex_content)

    def create_amount_input(self, transaction_type, error_message=None):
        """建立金額輸入 Flex Message"""
        title = f"新增{transaction_type.capitalize()}"
        alt_text = f"輸入{transaction_type.capitalize()}金額"
        
        body_contents = [
            {
                "type": "text",
                "text": "請輸入金額",
                "weight": "bold",
                "size": self.FONT_SIZE['md'],
                "margin": self.SPACING['lg']
            },
            {
                "type": "text",
                "text": "💡 範例: 150",
                "size": self.FONT_SIZE['sm'],
                "color": self.COLORS['text_muted'],
                "margin": self.SPACING['md']
            }
        ]
        
        flex_content = self._create_step_bubble(
            title=title,
            step_text="步驟 2/3 - 輸入金額",
            body_contents=body_contents,
            error_message=error_message
        )
        
        return FlexSendMessage(alt_text=alt_text, contents=flex_content)

    def create_description_input(self):
        """建立描述輸入 Flex Message"""
        body_contents = [
            {
                "type": "text",
                "text": "請輸入備註 (可選)",
                "weight": "bold",
                "size": self.FONT_SIZE['md'],
                "margin": self.SPACING['lg']
            },
            {
                "type": "text",
                "text": "💡 輸入任何文字作為備註，或點擊「跳過」",
                "size": self.FONT_SIZE['sm'],
                "color": self.COLORS['text_muted'],
                "margin": self.SPACING['md'],
                "wrap": True
            }
        ]
        
        flex_content = self._create_step_bubble(
            title="新增交易",
            step_text="步驟 3/3 - 輸入備註",
            body_contents=body_contents
        )
        
        # 添加跳過按鈕
        flex_content["footer"]["contents"].append({
            "type": "button",
            "style": "link",
            "height": "sm",
            "action": {
                "type": "message",
                "label": "跳過",
                "text": "跳過"
            }
        })
        
        return FlexSendMessage(alt_text="請輸入備註", contents=flex_content)

    def create_transaction_confirmation(self, transaction_type, data):
        """建立交易確認 Flex Message"""
        type_text = "收入" if transaction_type == 'income' else "支出"
        amount_color = self.COLORS['text_success'] if transaction_type == 'income' else self.COLORS['text_error']
        amount_text = f"+${data['amount']:,}" if transaction_type == 'income' else f"-${data['amount']:,}"

        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"確認新增{type_text}",
                        "weight": "bold",
                        "size": self.FONT_SIZE['lg']
                    }
                ],
                "backgroundColor": self.COLORS['bg_primary'],
                "paddingAll": self.SPACING['lg']
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    self._create_info_row("類型", type_text, amount_color),
                    self._create_info_row("分類", data['category']),
                    self._create_info_row("金額", amount_text, amount_color),
                    self._create_info_row("備註", data.get('description') or "無")
                ]
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "spacing": self.SPACING['sm'],
                "contents": [
                    {
                        "type": "button",
                        "style": "secondary",
                        "height": "sm",
                        "action": {"type": "message", "label": "取消", "text": "取消新增"}
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "height": "sm",
                        "color": self.COLORS['primary_green'],
                        "action": {"type": "message", "label": "確認新增", "text": "確認新增"}
                    }
                ]
            }
        }
        return FlexSendMessage(alt_text=f"確認新增{type_text}", contents=flex_content)

    def create_add_transaction_success(self, transaction_type, data):
        """建立新增交易成功 Flex Message"""
        type_text = "收入" if transaction_type == 'income' else "支出"
        header_color = self.COLORS['text_success'] if transaction_type == 'income' else self.COLORS['dark_green']
        amount_text = f"+${data['amount']:,}" if transaction_type == 'income' else f"-${data['amount']:,}"

        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"{type_text}記錄成功",
                        "weight": "bold",
                        "size": self.FONT_SIZE['lg'],
                        "color": self.COLORS['text_white']
                    },
                    {
                        "type": "text",
                        "text": amount_text,
                        "weight": "bold",
                        "size": "3xl",
                        "color": self.COLORS['text_white'],
                        "margin": self.SPACING['md']
                    }
                ],
                "backgroundColor": header_color,
                "paddingAll": self.SPACING['lg']
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    self._create_info_row("分類", data['category']),
                    self._create_info_row("備註", data.get('description') or "無"),
                    self._create_info_row("時間", datetime.now().strftime("%Y/%m/%d %H:%M"))
                ]
            }
        }
        return FlexSendMessage(alt_text=f"{type_text}成功", contents=flex_content)

    def _create_step_bubble(self, title, step_text, body_contents, error_message=None):
        """建立一個帶有步驟說明的標準泡泡"""
        header_contents = [
            {"type": "text", "text": title, "weight": "bold", "size": self.FONT_SIZE['lg']},
        ]
        if step_text:
            header_contents.append({
                "type": "text", 
                "text": step_text, 
                "size": self.FONT_SIZE['sm'], 
                "color": self.COLORS['text_secondary'], 
                "margin": self.SPACING['sm']
            })

        bubble = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": header_contents,
                "backgroundColor": self.COLORS['bg_primary'],
                "paddingAll": self.SPACING['lg']
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [],
                "paddingAll": self.SPACING['lg']
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "style": "secondary",
                        "height": "sm",
                        "action": {"type": "message", "label": "取消操作", "text": "取消操作"}
                    }
                ]
            }
        }
        
        if error_message:
            bubble["body"]["contents"].append(self._create_error_box(error_message))
            
        bubble["body"]["contents"].extend(body_contents)
        return bubble

    # 修正 _create_info_row 方法，支援自定義顏色
    def _create_info_row(self, label, value, value_color=None):
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
                    "flex": 2
                },
                {
                    "type": "text",
                    "text": str(value),
                    "wrap": True,
                    "color": value_color or self.COLORS['text_primary'],
                    "size": self.FONT_SIZE['sm'],
                    "flex": 3,
                    "weight": "bold" if value_color else "regular"
                }
            ],
            "margin": self.SPACING['sm']
        }

    # ====== 目標相關方法 ======
    def create_goal_title_input(self, error_message=None):
        """建立目標名稱輸入 Flex Message"""
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "新增目標",
                        "weight": "bold",
                        "size": self.FONT_SIZE['lg'],
                        "color": self.COLORS['text_primary']
                    },
                    {
                        "type": "text",
                        "text": "步驟 1/5 - 輸入目標名稱",
                        "size": self.FONT_SIZE['sm'],
                        "color": self.COLORS['text_secondary'],
                        "margin": self.SPACING['sm']
                    }
                ],
                "backgroundColor": self.COLORS['bg_primary'],
                "paddingAll": self.SPACING['lg']
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "請輸入您的目標名稱：",
                        "weight": "bold",
                        "size": self.FONT_SIZE['md'],
                        "color": self.COLORS['text_primary'],
                        "margin": self.SPACING['lg']
                    },
                    {
                        "type": "text",
                        "text": "💡 範例：買房頭期款、環遊世界基金",
                        "size": self.FONT_SIZE['sm'],
                        "color": self.COLORS['text_muted'],
                        "margin": self.SPACING['md']
                    }
                ]
            }
        }
        
        if error_message:
            flex_content["body"]["contents"].insert(0, self._create_error_box(error_message))
        
        flex_content["footer"] = {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "action": {
                        "type": "message",
                        "label": "取消操作",
                        "text": "取消操作"
                    }
                }
            ]
        }
        
        return FlexSendMessage(
            alt_text="請輸入目標名稱",
            contents=flex_content
        )

    def create_goal_type_selection(self, error_message=None):
        """建立目標類型選擇 Flex Message"""
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "新增目標",
                        "weight": "bold",
                        "size": self.FONT_SIZE['lg'],
                        "color": self.COLORS['text_primary']
                    },
                    {
                        "type": "text",
                        "text": "步驟 2/5 - 選擇目標類型",
                        "size": self.FONT_SIZE['sm'],
                        "color": self.COLORS['text_secondary'],
                        "margin": self.SPACING['sm']
                    }
                ],
                "backgroundColor": self.COLORS['bg_primary'],
                "paddingAll": self.SPACING['lg']
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": []
            }
        }

        if error_message:
            flex_content["body"]["contents"].append(self._create_error_box(error_message))

        selected_types = ["儲蓄", "投資", "債務"] # 這裡應該從 handler 傳入或定義在 theme 裡
        for type in selected_types:
            flex_content["body"]["contents"].append({
                "type": "button",
                "style": "link",
                "height": "sm",
                "action": {
                    "type": "message",
                    "label": type,
                    "text": f"選擇類型:{type}"
                },
                "margin": self.SPACING['sm']
            })
        
        flex_content["footer"] = {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "action": {
                        "type": "message",
                        "label": "取消操作",
                        "text": "取消操作"
                    }
                }
            ]
        }
        
        return FlexSendMessage(
            alt_text="選擇目標類型",
            contents=flex_content
        )

    def create_goal_amount_input(self, type, error_message=None):
        """建立目標金額輸入 Flex Message"""
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "新增目標",
                        "weight": "bold",
                        "size": self.FONT_SIZE['lg'],
                        "color": self.COLORS['text_primary']
                    },
                    {
                        "type": "text",
                        "text": f"步驟 3/5 - 輸入{type}金額",
                        "size": self.FONT_SIZE['sm'],
                        "color": self.COLORS['text_secondary'],
                        "margin": self.SPACING['sm']
                    }
                ],
                "backgroundColor": self.COLORS['bg_primary'],
                "paddingAll": self.SPACING['lg']
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"請輸入您的{type}目標金額：",
                        "weight": "bold",
                        "size": self.FONT_SIZE['md'],
                        "color": self.COLORS['text_primary'],
                        "margin": self.SPACING['lg']
                    },
                    {
                        "type": "text",
                        "text": "💡 範例：100000",
                        "size": self.FONT_SIZE['sm'],
                        "color": self.COLORS['text_muted'],
                        "margin": self.SPACING['md']
                    }
                ]
            }
        }
        
        if error_message:
            flex_content["body"]["contents"].insert(0, self._create_error_box(error_message))
        
        flex_content["footer"] = {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "action": {
                        "type": "message",
                        "label": "取消操作",
                        "text": "取消操作"
                    }
                }
            ]
        }
        
        return FlexSendMessage(
            alt_text=f"請輸入{type}目標金額",
            contents=flex_content
        )

    def create_goal_date_input(self, error_message=None):
        """建立目標日期輸入 Flex Message"""
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "新增目標",
                        "weight": "bold",
                        "size": self.FONT_SIZE['lg'],
                        "color": self.COLORS['text_primary']
                    },
                    {
                        "type": "text",
                        "text": "步驟 4/5 - 輸入目標完成日期",
                        "size": self.FONT_SIZE['sm'],
                        "color": self.COLORS['text_secondary'],
                        "margin": self.SPACING['sm']
                    }
                ],
                "backgroundColor": self.COLORS['bg_primary'],
                "paddingAll": self.SPACING['lg']
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "請輸入您的目標完成日期 (YYYY-MM-DD)：",
                        "weight": "bold",
                        "size": self.FONT_SIZE['md'],
                        "color": self.COLORS['text_primary'],
                        "margin": self.SPACING['lg']
                    },
                    {
                        "type": "text",
                        "text": "💡 範例：2025-12-31",
                        "size": self.FONT_SIZE['sm'],
                        "color": self.COLORS['text_muted'],
                        "margin": self.SPACING['md']
                    }
                ]
            }
        }
        
        if error_message:
            flex_content["body"]["contents"].insert(0, self._create_error_box(error_message))
        
        flex_content["footer"] = {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "action": {
                        "type": "message",
                        "label": "取消操作",
                        "text": "取消操作"
                    }
                }
            ]
        }
        
        return FlexSendMessage(
            alt_text="請輸入目標完成日期",
            contents=flex_content
        )

    def create_add_goal_confirmation(self, data):
        """建立新增目標確認 Flex Message"""
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "確認新增目標",
                        "weight": "bold",
                        "size": self.FONT_SIZE['lg'],
                        "color": self.COLORS['text_primary']
                    },
                    {
                        "type": "text",
                        "text": "步驟 5/5 - 最終確認",
                        "size": self.FONT_SIZE['sm'],
                        "color": self.COLORS['text_secondary'],
                        "margin": self.SPACING['sm']
                    }
                ],
                "backgroundColor": self.COLORS['bg_primary'],
                "paddingAll": self.SPACING['lg']
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    self._create_info_row("目標名稱", data['title']),
                    self._create_info_row("目標類型", data['type']),
                    self._create_info_row("目標金額", f"${data['target_amount']:,}"),
                    self._create_info_row("目標日期", data['target_date'])
                ]
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "spacing": self.SPACING['sm'],
                "contents": [
                    {
                        "type": "button",
                        "style": "secondary",
                        "height": "sm",
                        "action": {
                            "type": "message",
                            "label": "取消新增",
                            "text": "取消新增"
                        }
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "height": "sm",
                        "color": self.COLORS['primary_green'],
                        "action": {
                            "type": "message",
                            "label": "確認新增",
                            "text": "確認新增"
                        }
                    }
                ]
            }
        }
        
        return FlexSendMessage(
            alt_text=f"確認新增目標: {data['title']}",
            contents=flex_content
        )

    def create_add_goal_success(self, data):
        """建立新增目標成功 Flex Message"""
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "目標新增成功",
                        "weight": "bold",
                        "size": self.FONT_SIZE['lg'],
                        "color": self.COLORS['text_white']
                    },
                    {
                        "type": "text",
                        "text": "✅ 操作完成",
                        "size": self.FONT_SIZE['md'],
                        "color": self.COLORS['text_white'],
                        "margin": self.SPACING['md']
                    }
                ],
                "backgroundColor": self.COLORS['text_success'],
                "paddingAll": self.SPACING['lg']
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    self._create_info_row("目標名稱", data['title']),
                    self._create_info_row("目標類型", data['type']),
                    self._create_info_row("目標金額", f"${data['target_amount']:,}"),
                    self._create_info_row("目標日期", data['target_date']),
                    self._create_info_row("新增時間", datetime.now().strftime("%Y/%m/%d %H:%M"))
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "style": "link",
                        "height": "sm",
                        "action": {
                            "type": "message",
                            "label": "查看所有目標",
                            "text": "我的目標"
                        }
                    }
                ]
            }
        }
        
        return FlexSendMessage(
            alt_text=f"成功新增目標: {data['title']}",
            contents=flex_content
        )

    def create_goal_list_for_selection(self, goals, message=None):
        """建立目標列表供選擇 Flex Message"""
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "選擇目標",
                        "weight": "bold",
                        "size": self.FONT_SIZE['lg'],
                        "color": self.COLORS['text_primary']
                    },
                    {
                        "type": "text",
                        "text": message or "請輸入您要編輯的目標ID：",
                        "size": self.FONT_SIZE['sm'],
                        "color": self.COLORS['text_secondary'],
                        "margin": self.SPACING['sm']
                    }
                ],
                "backgroundColor": self.COLORS['bg_primary'],
                "paddingAll": self.SPACING['lg']
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": []
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "style": "secondary",
                        "height": "sm",
                        "action": {
                            "type": "message",
                            "label": "取消操作",
                            "text": "取消操作"
                        }
                    }
                ]
            }
        }

        for goal in goals:
            flex_content["body"]["contents"].append({
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": f"ID: {goal['id']}",
                        "size": self.FONT_SIZE['sm'],
                        "color": self.COLORS['text_primary'],
                        "flex": 1
                    },
                    {
                        "type": "text",
                        "text": goal['title'],
                        "size": self.FONT_SIZE['sm'],
                        "color": self.COLORS['text_primary'],
                        "flex": 2,
                        "wrap": True
                    },
                    {
                        "type": "text",
                        "text": f"${goal['target_amount']:,}",
                        "size": self.FONT_SIZE['sm'],
                        "color": self.COLORS['text_primary'],
                        "align": "end",
                        "flex": 1
                    }
                ],
                "margin": self.SPACING['sm']
            })
        
        return FlexSendMessage(
            alt_text="選擇目標",
            contents=flex_content
        )

    def create_edit_goal_selection(self, goal, editable_fields_keys, message=None):
        """建立編輯目標選擇 Flex Message"""
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "編輯目標",
                        "weight": "bold",
                        "size": self.FONT_SIZE['lg'],
                        "color": self.COLORS['text_primary']
                    },
                    {
                        "type": "text",
                        "text": "請選擇要編輯的欄位",
                        "size": self.FONT_SIZE['sm'],
                        "color": self.COLORS['text_secondary'],
                        "margin": self.SPACING['sm']
                    }
                ],
                "backgroundColor": self.COLORS['bg_primary'],
                "paddingAll": self.SPACING['lg']
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    # 顯示目標資訊
                    self._create_info_row("目標名稱", goal['title']),
                    self._create_info_row("目標類型", goal['type']),
                    self._create_info_row("目標金額", f"${goal['target_amount']:,}"),
                    self._create_info_row("目標日期", goal['target_date']),
                    {
                        "type": "separator",
                        "margin": self.SPACING['md']
                    },
                    {
                        "type": "text",
                        "text": "選擇要編輯的項目:",
                        "weight": "bold",
                        "size": self.FONT_SIZE['md'],
                        "color": self.COLORS['text_primary'],
                        "margin": self.SPACING['md']
                    },
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": self.SPACING['sm'],
                "contents": [
                    {
                        "type": "button",
                        "style": "secondary",
                        "height": "sm",
                        "action": {
                            "type": "message",
                            "label": "取消編輯",
                            "text": "取消操作"
                        }
                    }
                ]
            }
        }

        # Add editable fields as buttons
        for field_name in editable_fields_keys:
            flex_content["body"]["contents"].append({
                "type": "button",
                "style": "link",
                "height": "sm",
                "action": {
                    "type": "message",
                    "label": f"編輯{field_name}",
                    "text": field_name
                },
                "margin": self.SPACING['sm']
            })

        if message: 
            flex_content["body"]["contents"].insert(0, {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": message,
                        "size": self.FONT_SIZE['sm'],
                        "color": self.COLORS['text_error'],
                        "weight": "bold",
                        "wrap": True
                    }
                ],
                "backgroundColor": self.COLORS['bg_warning'],
                "paddingAll": self.SPACING['sm'],
                "cornerRadius": self.BORDER_RADIUS['sm'],
                "margin": self.SPACING['md']
            })
        
        return FlexSendMessage(
            alt_text=f"編輯目標: {goal['title']}",
            contents=flex_content
        )

    def create_edit_goal_success(self, goal, field, new_value):
        """建立編輯目標成功 Flex Message"""
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "目標編輯成功",
                        "weight": "bold",
                        "size": self.FONT_SIZE['lg'],
                        "color": self.COLORS['text_white']
                    },
                    {
                        "type": "text",
                        "text": "✅ 操作完成",
                        "size": self.FONT_SIZE['md'],
                        "color": self.COLORS['text_white'],
                        "margin": self.SPACING['md']
                    }
                ],
                "backgroundColor": self.COLORS['text_success'],
                "paddingAll": self.SPACING['lg']
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    self._create_info_row("目標名稱", goal['title']),
                    self._create_info_row("目標類型", goal['type']),
                    self._create_info_row("目標金額", f"${goal['target_amount']:,}"),
                    self._create_info_row("目標日期", goal['target_date']),
                    self._create_info_row("編輯時間", datetime.now().strftime("%Y/%m/%d %H:%M"))
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "style": "link",
                        "height": "sm",
                        "action": {
                            "type": "message",
                            "label": "查看所有目標",
                            "text": "我的目標"
                        }
                    }
                ]
            }
        }
        
        # Add specific field updated
        field_name_map = {
            "title": "目標名稱",
            "type": "目標類型",
            "target_amount": "目標金額",
            "target_date": "目標日期"
        }
        display_field_name = field_name_map.get(field, field)
        
        if field == "target_amount":
            new_value_display = f"${new_value:,}"
        else:
            new_value_display = new_value

        flex_content['body']['contents'].insert(0, self._create_info_row(f"更新欄位: {display_field_name}", new_value_display))

        return FlexSendMessage(
            alt_text=f"成功編輯目標: {goal['title']}",
            contents=flex_content
        )

    def create_edit_goal_field_input(self, field_name, goal, error_message=None):
        """建立編輯目標欄位輸入 Flex Message"""
        title_map = {
            "title": "目標名稱",
            "type": "目標類型",
            "target_amount": "目標金額",
            "target_date": "目標日期"
        }

        title = f"編輯{title_map.get(field_name, field_name)}"
        step_text = f"請輸入新的{title_map.get(field_name, field_name)}"

        # Get current value from goal object
        current_value = goal.get(field_name, "N/A")
        if field_name == "target_amount":
            current_value = f"${current_value:,}"

        body_contents = [
            {
                "type": "text",
                "text": f"目前值: {current_value}",
                "size": self.FONT_SIZE['sm'],
                "color": self.COLORS['text_muted'],
                "margin": self.SPACING['md']
            },
            {
                "type": "text",
                "text": step_text,
                "weight": "bold",
                "size": self.FONT_SIZE['md'],
                "color": self.COLORS['text_primary'],
                "margin": self.SPACING['lg']
            }
        ]

        if field_name == "target_date":
            body_contents.append({
                "type": "text",
                "text": "💡 格式：YYYY-MM-DD (例如: 2025-12-31)",
                "size": self.FONT_SIZE['sm'],
                "color": self.COLORS['text_muted'],
                "margin": self.SPACING['md']
            })
        elif field_name == "target_amount":
            body_contents.append({
                "type": "text",
                "text": "💡 範例：100000",
                "size": self.FONT_SIZE['sm'],
                "color": self.COLORS['text_muted'],
                "margin": self.SPACING['md']
            })

        flex_content = self._create_step_bubble(
            title=title,
            step_text="", # Step text is handled by body_contents
            body_contents=body_contents,
            error_message=error_message
        )

        return FlexSendMessage(
            alt_text=title,
            contents=flex_content
        )
    
    def create_edit_goal_confirmation(self, goal, field, new_value):
        """建立編輯目標確認 Flex Message"""
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "確認編輯目標",
                        "weight": "bold",
                        "size": self.FONT_SIZE['lg'],
                        "color": self.COLORS['text_primary']
                    },
                    {
                        "type": "text",
                        "text": "請確認以下變更",
                        "size": self.FONT_SIZE['sm'],
                        "color": self.COLORS['text_secondary'],
                        "margin": self.SPACING['sm']
                    }
                ],
                "backgroundColor": self.COLORS['bg_primary'],
                "paddingAll": self.SPACING['lg']
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": []
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "spacing": self.SPACING['sm'],
                "contents": [
                    {
                        "type": "button",
                        "style": "secondary",
                        "height": "sm",
                        "action": {
                            "type": "message",
                            "label": "取消編輯",
                            "text": "取消編輯"
                        }
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "height": "sm",
                        "color": self.COLORS['primary_green'],
                        "action": {
                            "type": "message",
                            "label": "確認編輯",
                            "text": "確認編輯"
                        }
                    }
                ]
            }
        }

        # Display the change
        old_value = goal.get(field, "N/A")
        if field == "target_amount":
            old_value = f"${old_value:,}"
            new_value_display = f"${new_value:,}"
        else:
            new_value_display = new_value

        flex_content['body']['contents'].append(self._create_info_row(field, f"{old_value} -> {new_value_display}"))

        return FlexSendMessage(
            alt_text=f"確認編輯目標: {goal['title']}",
            contents=flex_content
        )
    
    def create_delete_goal_confirmation(self, goal):
        """建立刪除目標確認 Flex Message"""
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "⚠️ 確認刪除目標",
                        "weight": "bold",
                        "size": self.FONT_SIZE['lg'],
                        "color": self.COLORS['text_white']
                    },
                    {
                        "type": "text",
                        "text": "步驟 2/2 - 最終確認",
                        "size": self.FONT_SIZE['sm'],
                        "color": self.COLORS['text_white'],
                        "margin": self.SPACING['sm']
                    }
                ],
                "backgroundColor": self.COLORS['text_error'],
                "paddingAll": self.SPACING['lg']
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "您即將刪除以下目標：",
                        "weight": "bold",
                        "size": self.FONT_SIZE['md'],
                        "color": self.COLORS['text_primary'],
                        "margin": self.SPACING['md']
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            self._create_info_row("目標名稱", goal['title']),
                            self._create_info_row("目標類型", goal['type']),
                            self._create_info_row("目標金額", f"${goal['target_amount']:,}"),
                            self._create_info_row("目標日期", goal['target_date'])
                        ],
                        "backgroundColor": self.COLORS['bg_card'],
                        "paddingAll": self.SPACING['md'],
                        "cornerRadius": self.BORDER_RADIUS['md'],
                        "margin": self.SPACING['md']
                    },
                    {
                        "type": "text",
                        "text": "⚠️ 此操作無法復原，請謹慎考慮！",
                        "size": self.FONT_SIZE['sm'],
                        "color": self.COLORS['text_error'],
                        "weight": "bold",
                        "wrap": True,
                        "margin": self.SPACING['lg']
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "horizontal",
                "spacing": self.SPACING['sm'],
                "contents": [
                    {
                        "type": "button",
                        "style": "secondary",
                        "height": "sm",
                        "action": {
                            "type": "message",
                            "label": "取消",
                            "text": "取消操作"
                        },
                        "flex": 1
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "height": "sm",
                        "color": self.COLORS['text_error'],
                        "action": {
                            "type": "message",
                            "label": "確認刪除",
                            "text": "確認刪除"
                        },
                        "flex": 1
                    }
                ]
            }
        }
        
        return FlexSendMessage(
            alt_text=f"確認刪除目標: {goal['title']}",
            contents=flex_content
        )
    
    def create_delete_goal_success(self, goal):
        """建立刪除目標成功 Flex Message"""
        flex_content = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "目標刪除成功",
                        "weight": "bold",
                        "size": self.FONT_SIZE['lg'],
                        "color": self.COLORS['text_white']
                    },
                    {
                        "type": "text",
                        "text": "✅ 操作完成",
                        "size": self.FONT_SIZE['md'],
                        "color": self.COLORS['text_white'],
                        "margin": self.SPACING['md']
                    }
                ],
                "backgroundColor": self.COLORS['text_success'],
                "paddingAll": self.SPACING['lg']
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "已成功刪除以下目標：",
                        "size": self.FONT_SIZE['md'],
                        "color": self.COLORS['text_primary'],
                        "margin": self.SPACING['md']
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            self._create_info_row("目標名稱", goal['title']),
                            self._create_info_row("目標類型", goal['type']),
                            self._create_info_row("刪除時間", datetime.now().strftime("%Y/%m/%d %H:%M"))
                        ],
                        "backgroundColor": self.COLORS['bg_success'],
                        "paddingAll": self.SPACING['md'],
                        "cornerRadius": self.BORDER_RADIUS['md'],
                        "margin": self.SPACING['md']
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "style": "link",
                        "height": "sm",
                        "action": {
                            "type": "message",
                            "label": "查看所有目標",
                            "text": "我的目標"
                        }
                    }
                ]
            }
        }
        
        return FlexSendMessage(
            alt_text=f"成功刪除目標: {goal['title']}",
            contents=flex_content
        )