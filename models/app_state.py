import time

class AppStateManager:
    """應用程式狀態管理器 - 處理系統層面的狀態"""

    def __init__(self, warmup_duration=30):
        self._startup_time = time.time()
        self._warmup_duration = warmup_duration
        self._is_warming_up = True

    def is_cold_start(self):
        """檢測是否為冷啟動期間"""
        current_time = time.time()
        startup_duration = current_time - self._startup_time

        #啟動後 30 秒內視為冷啟動期
        if startup_duration < self._warmup_duration:
            print(f"冷啟動檢測: 啟動後 {startup_duration:.1f} 秒")
            return True
        
        #第一次通過 30 秒時，標記為正常運行
        if self._is_warming_up:
            self._is_warming_up = False
            print("系統暖機完成，進入正常運行模式")

        return False
    
    def get_system_status(self):
        """獲取系統狀態"""
        current_time = time.time()
        uptime = current_time - self._startup_time
        
        return {
            "uptime": uptime,
            "status": "暖機中" if self._is_warming_up else "正常運行",
            "is_cold_start": self.is_cold_start()
        }

    def log_system_status(self):
        """紀錄系統狀態"""
        status_info = self.get_system_status()
        print(f"系統狀態: {status_info['status']}, 運行時間: {status_info['uptime']:.1f} 秒")