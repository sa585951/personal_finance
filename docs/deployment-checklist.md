# Deployment Checklist

更新：2026-11-09。僅規劃與驗收清單，不是已部署證明。
最新設定契約以 `docs/security-boundary-hardening.md` 為準。

## 本機到 staging

1. 先確認目標環境、DB 身分與備份；核對實際 migration head。
   本地目前 chain head 為 `20261109_0020`，不可直接拿測試 runner 連 staging／production。
2. migration 前核對可還原備份及適用版本；0018 新增短效 OAuth state，
   不授權刪除舊帳務或自動 downgrade。升級不代表歷史不平帳已修復。
3. Backend 設 `NOMICA_ENV=production`、`DEV_AUTH_BYPASS=false`、`FLASK_DEBUG=false`。
   使用 WSGI，不以 debug server 公開服務。
4. `FRONTEND_BASE_URL` 與 `VITE_BACKEND_BASE_URL` 都是同一個前端 HTTPS origin；
   LINE Console callback 為該 origin 的 `/line-login-callback`。
5. 核對 `frontend/vercel.json` 的 backend 目的地；其他平台須配置等效
   `/api/*`、`/line-login-start`、`/line-login-callback` 同源代理。
   前端正式 build 使用相對 API；不能沿用舊版跨站 localStorage Token 流程。
6. LINE 記帳預設啟用，`NOMICA_LINE_MODE` 可不設；舊值 `help_only` 也會進入記帳，
   要暫停 LINE 訊息互動時設 `disabled`。`NOMICA_LINE_HELP_USER_IDS` 已不讀取，可移除。
   LINE Gemini 需 `GEMINI_API_KEY` 與 `NOMICA_LINE_AI_PAID_PROJECT_VERIFIED=true`，
   月上限預設 5 USD，見 [LINE AI 試用](line-ai-pilot.md)。Web 一句話記帳只用本機規則；
   Web AI 維持 `NOMICA_AI_MODE=disabled`。
7. 憑證只存部署平台秘密設定；範例可版控，真實 `.env`、DB dump、Token 不可版控。
   依需求配置 JWT、DB、LINE Login 憑證；停用 AI 不需要為了部署加入 Gemini Key。
8. 協調 frontend/backend 版本與回退方案。回退不得直接刪除 state、命令或去重資料表。
9. 刪除帳號 30 天後的永久清除：`python -m scripts.purge_deleted_users` 預設只試跑並回報筆數，
   加 `--apply` 才寫入。建議每天排程一次（例如 Render Cron Job，指令同上並帶 `--apply`），
   沒有到期的資料時不會刪除任何東西。清除後只能從資料庫備份還原。

## staging 驗證（先用合成資料）

- 真 LINE Login 的 state／nonce、跨瀏覽器拒絕、重放拒絕與錯誤後重新登入。
- Callback URL 無 JWT；Cookie HttpOnly／Secure／SameSite=Lax；`/api/auth/me`
  登入後成功、登出後 401；重開、Safari／PWA 與代理不快取 Auth 回應。
- 寫入 Origin 驗證；公開 bypass/debug 不可使用；AI／LINE 停用入口不可產生解析或帳務。
- 手動交易與不同發票同帳戶並行、重送、編輯／刪除、Transfer、settlement、
  餘額不足及故障回滾，並核對 movement 與 reconciliation。
- 手機相機權限、前後鏡頭、圖片備援與返回流程；桌面 mock 不取代實機驗收。
- 查詢隔離、匯率與月報的驗收依現行財務合約；發布前保留版本與測試證據。

## 公開接收真實財務資料前

S1 的正式設定、S2 併發、S3 幣別／月報、S4 核心重試及 S5 的安全／隱私／
資料控制門檻須收斂，不能只因本機測試通過就公開。M2 已有限證據收尾，
原 5 至 10 人招募不是目前開發阻塞；研究可用合成資料平行進行。

匯出資料、帳號刪除與登出所有裝置已有本機實作與測試；刪除後 30 天的自動清除排程、
正式金鑰限制／Billing、保留政策及適用平台要求仍須逐項取得證據。
AI 如要開放，另通過 G-AI；這次停用不等於已完成額度或預算 gateway。
正式產品交付依 S6，iOS 不自動啟動。

## R09／0019 升級前置

0019 新增成員／分攤唯一性；正式與既有 QA DB 尚未套用。
備份、暫停相關寫入，先核對重複資料與資料量；發現重複會停止，不自動清資料。
不得為通過 migration 任意刪除或合併帶財務歷史的 member／split。
在隔離副本驗證並核定清理方案後才重試，評估 DDL 鎖與維護時間；不要把
專用 DB 的成功升級當成正式資料已可升級。0018 OAuth 設定仍需一併核對。
