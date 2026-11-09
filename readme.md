# Nomica

在 LINE 裡一句話記帳，旅行分帳自動回到你的個人帳本。

Nomica 是一本帳的多個入口：

- **Web／PWA**：完整帳本，包含今天、明細、記一筆、旅行與分帳結算、帳戶、預算、分析。
- **LINE**：快速記帳的窗口。用一句話產生草稿，確認後才入帳。
- **iOS App**：規劃中，現有的唯讀原型暫緩，見 [`ios/Nomica/README.md`](ios/Nomica/README.md)。

三個入口共用同一組後端 API 與帳務規則。Nomica 不提供行情、選股或投資建議。

文件入口：[`docs/README.md`](docs/README.md)。

## 架構

| 層 | 技術 | 部署 |
| --- | --- | --- |
| 後端 API、LINE webhook | Python 3.12、Flask、SQLAlchemy Core、Alembic | Render |
| 資料庫 | PostgreSQL | Supabase |
| Web／PWA | Vue 3、Vite、Vue Router | Vercel（同源代理 `/api/*` 與 LINE 登入） |
| LINE | LINE Login、Messaging API；Gemini 解析需使用者同意 | 與後端同部署 |

```text
web_app.py              Flask API、LINE 登入與 webhook
models/                 帳務、旅行、預算、隱私、LINE 與 AI 解析
alembic/versions/       資料庫 migration
tests/                  後端測試（含 PostgreSQL smoke）
frontend/src/           Vue 頁面與元件
frontend/scripts/       樣式檢查、mock UI 回歸、端對端測試
ios/Nomica/             iOS 唯讀原型（暫緩）
.github/workflows/      CI
```

## 本機開發

```bash
docker compose up -d postgres
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # 依註解填入
alembic upgrade head
python web_app.py
```

```bash
cd frontend
npm install
npm run dev
```

本機不想走 LINE 登入時，後端設 `DEV_AUTH_BYPASS=true`、前端設 `VITE_DEV_AUTH_BYPASS=true`。只接受 loopback，production 會拒絕啟動。

## 測試

```bash
# 後端全量；DB 測試需要名稱以 _test 結尾的本機資料庫
RUN_DB_SMOKE_TESTS=1 TEST_DATABASE_URL=postgresql://personal_finance:personal_finance@localhost:5433/personal_finance_test pytest -q

cd frontend
npm run lint && npm run check:styles && npm run build
npm run test:ui     # mock API 的 UI 回歸（多尺寸、深淺色）
npm run test:e2e    # 真實瀏覽器 → Vite → Flask → PostgreSQL
```

CI（`.github/workflows/ci.yml`）在每個 PR 執行以上全部。

唯讀帳戶對帳：

```bash
python -m scripts.reconcile_accounts --fail-on-issues
```

## 部署

依 [`docs/deployment-checklist.md`](docs/deployment-checklist.md)。環境變數與說明見 [`.env.example`](.env.example)；LINE AI 的啟用見 [`docs/line-ai-pilot.md`](docs/line-ai-pilot.md)。
