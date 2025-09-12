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