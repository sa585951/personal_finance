from datetime import datetime
from linebot.models import FlexSendMessage

class TransferFlowHandler:
    """轉帳流程處理器"""
    
    def __init__(self, asset_manager, user_state_manager):
        self.asset_manager = asset_manager
        self.user_state_manager = user_state_manager
    
    def start_flow(self, user_id):
        """開始轉帳流程"""
        try:
            # 獲取所有帳戶
            assets = self.asset_manager.get_all_assets()
            
            if len(assets) < 2:
                return "您需要至少兩個帳戶才能進行轉帳\n請先新增更多帳戶"
            
            # 設定用戶狀態
            self.user_state_manager.set_user_state(
                user_id, 'transfer_flow', 'select_source'
            )
            
            return self._create_account_selection_flex(
                assets, "請選擇轉出帳戶", "source"
            )
            
        except Exception as e:
            return f"轉帳流程啟動失敗: {str(e)}"
    
    def handle_flow_message(self, user_id, message, current_state):
        """處理轉帳流程中的訊息"""
        step = current_state['step']
        
        if step == 'select_source':
            return self._handle_source_selection(user_id, message)
        elif step == 'select_target':
            return self._handle_target_selection(user_id, message)
        elif step == 'input_amount':
            return self._handle_amount_input(user_id, message, current_state)
        elif step == 'confirm':
            return self._handle_confirmation(user_id, message, current_state)
        else:
            # 未知步驟，重置流程
            self.user_state_manager.clear_user_state(user_id)
            return "轉帳流程異常，已重置。請重新開始"
    
    def _handle_source_selection(self, user_id, message):
        """處理來源帳戶選擇"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "轉帳已取消"
        
        if not message.startswith("選擇帳戶:"):
            return "請點擊按鈕選擇帳戶，或輸入「取消操作」"
        
        source_account_key = message.replace("選擇帳戶:", "")
        
        # 驗證帳戶存在
        assets = self.asset_manager.get_all_assets()
        if source_account_key not in assets:
            return "選擇的帳戶不存在，請重新選擇"
        
        # 更新狀態到下一步
        self.user_state_manager.update_user_state(
            user_id, 
            step='select_target',
            data={'source_account': source_account_key}
        )
        
        # 過濾掉來源帳戶，顯示目標帳戶選擇
        target_assets = {k: v for k, v in assets.items() if k != source_account_key}
        
        return self._create_account_selection_flex(
            target_assets, "請選擇轉入帳戶", "target"
        )
    
    def _handle_target_selection(self, user_id, message):
        """處理目標帳戶選擇"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "轉帳已取消"
        
        if not message.startswith("選擇帳戶:"):
            return "請點擊按鈕選擇帳戶，或輸入「取消操作」"
        
        target_account_key = message.replace("選擇帳戶:", "")
        
        # 更新狀態
        self.user_state_manager.update_user_state(
            user_id,
            step='input_amount',
            data={'target_account': target_account_key}
        )
        
        # 獲取來源帳戶資訊
        current_state = self.user_state_manager.get_user_state(user_id)
        source_key = current_state['data']['source_account']
        assets = self.asset_manager.get_all_assets()
        source_balance = assets[source_key]['balance']
        
        return f"請輸入轉帳金額\n\n來源帳戶餘額: ${source_balance:,.0f}\n\n輸入範例: 1000"
    
    def _handle_amount_input(self, user_id, message, current_state):
        """處理金額輸入"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "轉帳已取消"
        
        try:
            amount = float(message.replace(',', ''))
            if amount <= 0:
                return "金額必須大於 0，請重新輸入"
            
            # 檢查餘額
            source_key = current_state['data']['source_account']
            assets = self.asset_manager.get_all_assets()
            source_balance = assets[source_key]['balance']
            
            if amount > source_balance:
                return f"金額超過帳戶餘額 ${source_balance:,.0f}，請重新輸入"
            
            # 更新狀態
            self.user_state_manager.update_user_state(
                user_id,
                step='confirm',
                data={'amount': amount}
            )
            
            return self._create_transfer_confirmation_flex(current_state['data'], amount)
            
        except ValueError:
            return "請輸入有效的數字金額"
    
    def _handle_confirmation(self, user_id, message, current_state):
        """處理確認轉帳"""
        if message == "確認轉帳":
            # 執行轉帳
            data = current_state['data']
            success, result_message = self.asset_manager.transfer(
                data['source_account'],
                data['target_account'],
                data['amount']
            )
            
            # 清除狀態
            self.user_state_manager.clear_user_state(user_id)
            
            if success:
                return self._create_transfer_success_flex(data)
            else:
                return f"轉帳失敗: {result_message}"
        
        elif message == "取消轉帳":
            self.user_state_manager.clear_user_state(user_id)
            return "轉帳已取消"
        else:
            return "請點擊「確認轉帳」或「取消轉帳」"
    
    def _create_account_selection_flex(self, assets, title, selection_type):
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
    
    def _create_transfer_confirmation_flex(self, data, amount):
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
    
    def _create_transfer_success_flex(self, data):
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
    
class AddAccountFlowHandler:
    """新增帳戶流程處理器"""
    
    def __init__(self, asset_manager, user_state_manager):
        self.asset_manager = asset_manager
        self.user_state_manager = user_state_manager
        
        # 帳戶類型選項
        self.account_types = ["活存", "定存", "投資", "其他"]
    
    def start_flow(self, user_id):
        """開始新增帳戶流程"""
        try:
            # 設定用戶狀態
            self.user_state_manager.set_user_state(
                user_id, 'add_account_flow', 'input_bank_name'
            )
            
            return "請輸入銀行名稱\n\n範例：玉山銀行、台灣銀行、中國信託\n\n或輸入「取消操作」"
            
        except Exception as e:
            return f"新增帳戶流程啟動失敗: {str(e)}"
    
    def handle_flow_message(self, user_id, message, current_state):
        """處理新增帳戶流程中的訊息"""
        step = current_state['step']
        
        if step == 'input_bank_name':
            return self._handle_bank_name_input(user_id, message)
        elif step == 'select_account_type':
            return self._handle_account_type_selection(user_id, message, current_state)
        elif step == 'input_balance':
            return self._handle_balance_input(user_id, message, current_state)
        elif step == 'confirm':
            return self._handle_confirmation(user_id, message, current_state)
        else:
            # 未知步驟，重置流程
            self.user_state_manager.clear_user_state(user_id)
            return "新增帳戶流程異常，已重置。請重新開始"
    
    def _handle_bank_name_input(self, user_id, message):
        """處理銀行名稱輸入"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "新增帳戶已取消"
        
        # 簡單驗證銀行名稱
        bank_name = message.strip()
        if len(bank_name) < 2:
            return "請輸入有效的銀行名稱（至少2個字）"
        
        if len(bank_name) > 20:
            return "銀行名稱太長，請重新輸入"
        
        # 更新狀態到下一步
        self.user_state_manager.update_user_state(
            user_id,
            step='select_account_type',
            data={'bank_name': bank_name}
        )
        
        return self._create_account_type_selection_flex()
    
    def _handle_account_type_selection(self, user_id, message, current_state):
        """處理帳戶類型選擇"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "新增帳戶已取消"
        
        if not message.startswith("選擇類型:"):
            return "請點擊按鈕選擇帳戶類型，或輸入「取消操作」"
        
        account_type = message.replace("選擇類型:", "")
        
        if account_type not in self.account_types:
            return "請選擇有效的帳戶類型"
        
        # 更新狀態
        self.user_state_manager.update_user_state(
            user_id,
            step='input_balance',
            data={'account_type': account_type}
        )
        
        return "請輸入帳戶初始餘額\n\n範例：50000\n\n注意：金額不能為負數"
    
    def _handle_balance_input(self, user_id, message, current_state):
        """處理餘額輸入"""
        if message == "取消操作":
            self.user_state_manager.clear_user_state(user_id)
            return "新增帳戶已取消"
        
        try:
            balance = float(message.replace(',', ''))
            if balance < 0:
                return "餘額不能為負數，請重新輸入"
            
            # 更新狀態
            self.user_state_manager.update_user_state(
                user_id,
                step='confirm',
                data={'balance': balance}
            )
            
            return self._create_add_account_confirmation_flex(current_state['data'], balance)
            
        except ValueError:
            return "請輸入有效的數字金額"
    
    def _handle_confirmation(self, user_id, message, current_state):
        """處理確認新增"""
        if message == "確認新增":
            # 執行新增帳戶
            data = current_state['data']
            success, result_message = self.asset_manager.add_account(
                data['bank_name'],
                data['account_type'],
                data['balance']
            )
            
            # 清除狀態
            self.user_state_manager.clear_user_state(user_id)
            
            if success:
                return self._create_add_account_success_flex(data)
            else:
                return f"新增帳戶失敗: {result_message}"
        
        elif message == "取消新增":
            self.user_state_manager.clear_user_state(user_id)
            return "新增帳戶已取消"
        else:
            return "請點擊「確認新增」或「取消新增」"
    
    def _create_account_type_selection_flex(self):
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
        for account_type in self.account_types:
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
    
    def _create_add_account_confirmation_flex(self, data, balance):
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
                            "text": "取消新增"
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
    
    def _create_add_account_success_flex(self, data):
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