# models/database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from dotenv import load_dotenv
from .schema import metadata
from contextlib import contextmanager

# 從 .env 檔案載入環境變數
load_dotenv()

# 從環境變數中取得資料庫連線 URL
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise EnvironmentError("DATABASE_URL 環境變數未設定，請檢查 .env 檔案。")

# 建立一個可供整個應用程式重複使用的 engine
# pool_recycle: 設定連線回收時間，例如 1800 秒 (30分鐘)，避免連線因閒置而被資料庫伺服器切斷
# pool_pre_ping: 在從連線池取出連線前，先進行一次簡單的 ping 測試，確保連線是有效的
engine = create_engine(
    DATABASE_URL,
    pool_recycle=1800,
    pool_pre_ping=True 
)

# 建立一個 Session 工廠，它將為我們生產 Session 物件
# autocommit=False 和 autoflush=False 是推薦的設定
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 使用 scoped_session 來確保每個 Web 請求都使用獨立的 Session
# 這是一個執行緒安全的 Session 物件。
# 我們將在應用程式層級 (例如 Flask 的 @app.teardown_appcontext) 中管理 session 的生命週期。
db_session = scoped_session(SessionLocal)

# 確保所有在 schema.py 中定義的資料表都被創建
# 這行可以保留，用於初次啟動時建表，但在生產環境中建議註解掉
# metadata.create_all(engine)