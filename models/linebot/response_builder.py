from linebot.models import TextSendMessage
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
    
    # === 錯誤和幫助訊息 ===
    def create_error_message(self, message):
        """建立錯誤訊息"""
        return TextSendMessage(text=f"❌ {message}")
    
    def create_help_message(self, is_cold_start=False):
        """建立幫助訊息"""
        base_message = """歡迎使用個人財務助手！

支援功能：
💰 記帳：
- "午餐花了150"
- "買咖啡50元"  
- "薪水入帳30000"

📊 查詢：
- "查詢本月支出"
- "我的資產"

🏦 資產管理：
- "新增銀行帳戶"
- "我要轉帳"
- "更新餘額"

範例：
早餐花80元、搭捷運30、薪水45000"""
        
        if is_cold_start:
            base_message += "\n\n💡 提示：系統剛啟動，如無回應請重新發送"
        
        return TextSendMessage(text=base_message)