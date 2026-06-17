from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class BaseTheme:
    """基礎設計規範 - 參考記帳小旺來風格"""

    DEFAULT_DISPLAY_TIMEZONE = "Asia/Taipei"
    
    # 主色系 (模仿小旺來的溫暖綠色調)
    COLORS = {
        # 主要顏色
        'primary_green': '#4CAF50',      # 主綠色
        'light_green': '#81C784',        # 淺綠色
        'dark_green': '#388E3C',         # 深綠色
        'accent_orange': '#FF9800',      # 橘色強調
        'soft_yellow': '#FFEB3B',        # 溫暖黃色
        
        # 背景色 (溫和色調)
        'bg_primary': '#F8F9FA',         # 主背景
        'bg_card': '#FFFFFF',            # 卡片背景
        'bg_success': '#E8F5E8',         # 成功背景
        'bg_info': '#E3F2FD',            # 資訊背景
        'bg_warning': '#FFF8E1',         # 警告背景
        'bg_error': '#FFEBEE',           # 錯誤背景
        
        # 文字色 (柔和對比)
        'text_primary': '#2E2E2E',       # 主要文字
        'text_secondary': '#666666',     # 次要文字
        'text_muted': '#999999',         # 淡化文字
        'text_white': '#FFFFFF',         # 白色文字
        'text_success': '#4CAF50',       # 成功文字
        'text_error': '#F44336',         # 錯誤文字
    }
    
    # 間距系統 (舒適的視覺節奏)
    SPACING = {
        'xs': '4px',
        'sm': '8px',
        'md': '12px',
        'lg': '16px',
        'xl': '20px',
        'xxl': '24px'
    }
    
    # 字體大小
    FONT_SIZE = {
        'xs': 'xs',
        'sm': 'sm',
        'md': 'md', 
        'lg': 'lg',
        'xl': 'xl',
        'xxl': 'xxl',
        '3xl': '3xl',
        '4xl': '4xl'
    }
    
    # 圓角 (溫和圓潤)
    BORDER_RADIUS = {
        'sm': '6px',
        'md': '12px',
        'lg': '16px'
    }
    
    # 分類顏色 (溫和但有辨識度)
    CATEGORY_COLORS = {
        "伙食": "#66BB6A",     # 綠色
        "交通": "#42A5F5",     # 藍色
        "購物": "#FFA726",     # 橘色
        "娛樂": "#EC407A",     # 粉紅
        "醫療": "#EF5350",     # 紅色
        "投資": "#78909C",     # 藍灰
        "生活": "#8D6E63",     # 咖啡色
        "其他": "#BDBDBD"      # 灰色
    }

    def _format_display_time(self, timezone_name=None):
        """LINE 顯示用時間，避免 Render 等 UTC 環境讓使用者看到錯誤時區。"""
        display_timezone = timezone_name or self.DEFAULT_DISPLAY_TIMEZONE
        try:
            tzinfo = ZoneInfo(display_timezone)
        except ZoneInfoNotFoundError:
            tzinfo = ZoneInfo(self.DEFAULT_DISPLAY_TIMEZONE)
        return datetime.now(tzinfo).strftime("%Y/%m/%d %H:%M")
