from ..ai_parse_service import AIParseService


class MessageParser:
    """統一的訊息解析入口，協調不同解析器的使用"""
    
    def __init__(self, gemini_model, prompt_template):
        """
        初始化訊息解析器
        
        Args:
            gemini_model: Gemini 模型實例
            prompt_template (str): Prompt 模板
            cold_start_checker (callable, optional): 冷啟動檢測函數
        """
        self.ai_parse_service = AIParseService(
            gemini_model=gemini_model,
            prompt_template=prompt_template,
        )
    
    def parse(self, message):
        """
        解析訊息的主要入口
        
        Args:
            message (str): 用戶訊息
            
        Returns:
            dict: 解析結果
        """
        return self.ai_parse_service.parse_legacy(message)

    def parse_shared(self, message):
        """解析訊息並回傳跨平台共用格式。"""
        return self.ai_parse_service.parse(message)
