import os
from sqlalchemy import create_engine
from dotenv import load_dotenv
from .schema import metadata # Import metadata

# 從 .env 檔案載入環境變數
load_dotenv()

# 從環境變數中取得資料庫連線 URL
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise EnvironmentError("DATABASE_URL 環境變數未設定，請檢查 .env 檔案。")

# 建立一個可供整個應用程式重複使用的 engine
engine = create_engine(DATABASE_URL)

# 確保所有在 schema.py 中定義的資料表都被創建
metadata.create_all(engine)
