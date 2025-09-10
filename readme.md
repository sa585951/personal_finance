# 個人財務管理系統 (Personal Finance App)

這是一個以 Python 和 Flask 打造的 RESTful API 後端，用於管理個人資產、預算與財務目標。

## 🎯 專案定位
- **類型**：全端 Side Project
- **功能**：資產追蹤、預算管理、財務目標、報表視覺化
- **技術亮點**：Flask + Vue 3 + PostgreSQL + Render/Vercel 部署
- **實用性**：幫助使用者管理個人財務，適合擴展為 SaaS 應用

## 🛠 技術棧
- **後端**: Python (Flask)
- **前端**: Vue 3 + Vite
- **資料庫**: PostgreSQL
- **圖表**: Chart.js + vue-chartjs
- **部署**: Render (後端/DB), Vercel (前端)

## 📈 功能列表
- 資產管理：多銀行帳戶追蹤  
- 交易紀錄：收入 / 支出分類  
- 預算設定：每月類別預算 + 超支追蹤  
- 財務目標：進度追蹤  
- 視覺化：月度支出分佈圖、資產變化圖表  

## 🚀 未來優化方向
- 多使用者系統 (登入、權限控管)  
- 自動化 API（股價、匯率）  
- ML 預算/支出預測  
- CI/CD + Docker + Kubernetes 部署  


## 專案架構

-   `main.py`: 專案的主程式入口，提供一個命令列介面 (CLI) 進行測試與互動。
-   `web_app.py`: Flask 網頁應用程式的入口，提供完整的 RESTful API 接口。
-   `models/`: 包含核心業務邏輯。
    -   `asset_manager.py`: 管理資產帳戶。
    -   `budget_manager.py`: 管理預算與支出。
    -   `goal_manager.py`: 管理財務目標。
-   `reports/`: 包含所有顯示報表與格式化的邏輯。
-   `data/`: 存放所有 JSON 格式的資料檔案。
-   `config.py`: 專案的通用設定檔。
-   `utils.py`: 專案的通用工具函數。


## 🔗 Demo / GitHub
- [GitHub Repo](#)  
- [Demo 連結](#)  

## 安裝與執行

### 1. 克隆專案

首先，從 GitHub 將專案克隆到你的電腦上。

```bash
git clone [https://github.com/你的用戶名/你的專案名.git](https://github.com/你的用戶名/你的專案名.git)
cd 你的專案名

# 建立一個名為 .venv 的虛擬環境
python -m venv .venv

# 啟用虛擬環境
# 在 Windows 上 (使用 PowerShell 或 CMD)：
.\.venv\Scripts\activate

# 在 macOS / Linux 上：
source ./.venv/bin/activate

pip install Flask

# 請確保你在專案的根目錄
python main.py
# 請確保你在專案的根目錄
python web_app.py
```
