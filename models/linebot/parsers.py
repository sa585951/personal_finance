import json

class GeminiParser:
    def __init__(self, model, prompt_template, cold_start_checker=None):
        """初始化 Gemini 解析器
        
        Args:
            model: Gemini 模型實例
            prompt_template (str): Prompt 模板
            cold_start_checker (callable, optional): 冷啟動檢測函數"""
        
        self.model = model
        self.prompt_template = prompt_template
        self.cold_start_checker = cold_start_checker

    def parse(self,message):
        """
        使用 Gemini 解析自然語言
        
        Args:
            message (str): 用戶訊息
            
        Returns:
            dict: 解析結果
        """
        try:
            prompt = self.prompt_template.format(message = message)
            response = self.model.generate_content(prompt)

            # 清理回應
            cleaned_text = self._clean_response(response.text)
            result = json.loads(cleaned_text)

            return self._validate_result(result, message)
        
        except Exception as e:
            print(f"Gemini 解析失敗: {e}")

            # 冷啟動期間的特殊處理
            if self.cold_start_checker and self.cold_start_checker():
                print("冷啟動期間 Gemini 失敗， 可能是網路連線還沒穩定")

            return {"type": "other", "error": str(e)}
        
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
            result["description"] = self._normalize_description(
                result.get("description"), original_message, result.get("category")
            )
            if "target_asset" not in result:
                result["target_asset"] = None

        elif result["type"] == "income":
            if "amount" not in result or not isinstance(result["amount"], (int, float)):
                result["type"] = "other"
                result["error"] = "無法識別收入金額"
            result["description"] = self._normalize_description(
                result.get("description"), original_message, result.get("category")
            )
            if "target_asset" not in result:
                result["target_asset"] = None

        return result

    def _normalize_description(self, description, original_message, category=None):
        if description is None:
            return ""

        normalized = str(description).strip()
        if not normalized:
            return ""

        if normalized in {"支出", "收入", "記帳"}:
            return ""

        if normalized == str(original_message).strip():
            return ""

        if category is not None and normalized == str(category).strip():
            return ""

        return normalized

class QuickParser:
    """快速解析器 - 使用規則匹配來快速識別常見的訊息類型"""
    
    def parse(self, message):
        """
        快速解析規則
        
        Args:
            message (str): 用戶訊息
            
        Returns:
            dict or None: 解析結果，如果返回 None 表示需要 Gemini 處理
        """
        # 財務目標功能目前暫停，舊版目標按鈕 payload 不再進入流程。
        if message.startswith(("編輯目標:", "刪除目標:")):
            return {"type": "other"}

        message_lower = message.lower()
        has_amount_hint = any(char.isdigit() for char in message)

        # 刪除相關 - 最具體的先匹配
        if any(word in message_lower for word in ['刪除帳戶', '刪除資產', '移除帳戶']):
            return {"type": "start_delete_asset"}
        
        if message_lower in ['刪除交易', '刪除記錄', '刪除支出']:
            return {"type": "start_delete_transaction"}
        
        # 更新相關
        if any(word in message_lower for word in ['更新餘額', '修改帳戶餘額', '調整餘額']):
            return {"type": "start_update_balance"}
        
        # 新增相關
        if any(word in message_lower for word in ['快速記帳', '新增支出']):
            return {"type": "start_add_expense"}

        if any(word in message_lower for word in ['紀錄收入', '新增收入']):
            return {"type": "start_add_income"}

        if any(word in message_lower for word in ['新增銀行帳戶', '新增帳戶', '加入帳戶']):
            return {"type": "start_add_account"}
        
        # 轉帳相關
        if any(word in message_lower for word in ['我要轉帳', '轉帳', '帳戶間轉帳']):
            return {"type": "start_transfer"}

        # 投資投入/定期定額目前屬於資金流向，應走帳戶互轉，不建立一般支出。
        if has_amount_hint and any(word in message_lower for word in [
            '定期定額', '買股票', '買基金', '買etf', '投入投資', '投資帳戶', '券商'
        ]):
            return {"type": "other", "error": "investment_allocation_requires_transfer"}
        
        # 查詢相關 - 放在後面，避免被 "餘額" 等關鍵字誤觸
        if any(word in message_lower for word in ['查詢', '統計', '本月']) or (
            '支出' in message_lower and not has_amount_hint
        ):
            return {"type": "query"}
        
        if any(word in message_lower for word in ['資產', '總資產']):
            return {"type": "asset_query"}
        
        # 預算相關
        if any(word in message_lower for word in ['設定預算', '新增預算', '調整預算']):
            return {"type": "start_set_budget"}

        # 財務目標功能目前暫停，不主動進入舊版 LINE 目標流程。
        if any(word in message_lower for word in [
            '財務目標', '我的目標', '目標查詢', '新增目標', '設定目標',
            '管理目標', '編輯目標', '目標進度', '進度查詢'
        ]):
            return {"type": "other"}

        if any(word in message_lower for word in ['幫助', '說明', '功能', '測試']):
            return {"type": "help"}
        
        # 記帳類交給 Gemini
        if has_amount_hint:
            return None
        
        return {"type": "other", "error": "unrecognized_input"}
