# S1 安全邊界修補

## R01：旅行列表與個人月報查詢

`GET /api/transactions` 不接受同時提供有效 `trip_id` 與
`monthly_report=true`，回應 400。旅行列表與個人月報分別沿用既有查詢，
避免旅行列表分支引用未 join 的 `transaction_splits`。

回歸包含 Manager 的查詢前拒絕、Flask API 400，以及兩條正常查詢的
PostgreSQL SQL 編譯檢查。這些檢查不等同正式資料影響或完整資料隔離驗收。
本項不修改歷史帳務、不需要 migration。

## R02 / U06：旅行對話框純文字輸出

邀請、結算摘要與 CSV 的手動複製備援，以 DOM textarea 的 `value`
設定內容；刪除對話框以 `text` 顯示共享名稱。不得將使用者文字插入 HTML。
`test:ui` 使用真實 SweetAlert 與 TripsView methods，驗證 textarea 跳脫字串及
惡意旅行名稱不產生 img/svg 或執行事件，並確認取消不執行刪除。
本項只處理 HTML 邊界；CSV 公式安全仍獨立追蹤 R25。

## R12：Browser-bound 單次 LINE 登入

Migration `20261021_0018` 僅新增 `oauth_login_states`，不修改使用者或帳務。
state 與瀏覽器秘密各自隨機產生，DB 僅存其 SHA256；以 callback 專用的
HttpOnly、SameSite=Lax Cookie 綁定瀏覽器，10 分鐘到期。開始新登入時清除
過期登入 metadata；多分頁以最後一次登入的 Cookie 為準，舊分頁須重新開始。

callback 透過單一條件 UPDATE 消耗 state 並先 commit，再交換 Provider token；
即使交換失敗也不能重放，須重新登入。ID token 另驗證對應 nonce；交換設 10 秒 timeout。
Auth 回應禁止快取／Referrer，錯誤不輸出 Provider 或 DB 詳情。

回歸包含不符／缺少 Cookie、過期／竄改／重放、nonce 與 HTTP 交換邊界，
以及隔離 PostgreSQL 多連線僅一次消耗、跨 Session 保留狀態和含帳務 0017 升級。
Provider 使用替身，不等於真實 LINE 登入／手機驗收。

## R13 / R14：Web Cookie 與公開設定

Web callback 不再傳 Token；前端清除既有 `authToken` 並改以 `/api/auth/me`
驗證 Cookie session，router、Navbar、Axios 同步切換。Bearer API 留給明確的
非瀏覽器 client；不批次撤銷既有 session，因此歷史已曝光憑證的處置仍需另行核對。
Cookie 為 host-only、HttpOnly、production Secure、SameSite=Lax；寫入仍檢查 Origin。

正式環境以同源 proxy 避免第三方 Cookie 被 Safari/PWA 阻擋：

1. 先備份並將目標 DB 升至 `20261021_0018`，不要在正式環境執行測試。
2. `NOMICA_ENV=production`（兼容 `FLASK_ENV`，兩者都缺省時以 production 判定）；
   `DEV_AUTH_BYPASS=false`、`FLASK_DEBUG=false`。
3. Backend 的 `FRONTEND_BASE_URL` 及 `VITE_BACKEND_BASE_URL` 都設為同一個前端
   HTTPS origin；後者在此是瀏覽器可達的 OAuth callback origin，不是內網位址。
4. LINE Console callback 改為該 origin 的 `/line-login-callback`。
5. `frontend/vercel.json` 已加入 `/api/*` 與 `/line-login-*` 的代理，目的地沿用
   原 Vite 設定中的 Render host。部署前核對實際 backend host；其他平台提供等效代理。
6. 前後端須協調切換，前端 production 使用相對 URL，忽略 dev-only `VITE_APP_API_URL`。
   先在 staging 驗證 Cookie／Origin、登入、登出、重開及 callback，再開放登入。

未配置同源 HTTPS、未知環境、公開環境 bypass/debug 或 development 的公開 URL
會拒絕啟動。開發 bypass 還限制 request host 與來源 IP 為 loopback；正式 build
若含 `VITE_DEV_AUTH_BYPASS=true` 會失敗。development 須使用 localhost/127.0.0.1
且前後端維持同一 hostname；相對 API 的 Vite proxy 預設指向本機 5000，可用
`NOMICA_DEV_API_TARGET` 明確指定。直接 `python web_app.py` 僅限本機，正式使用 WSGI。

新 Auth 與 API 路徑不進 Service Worker cache。瀏覽器回歸含 Cookie session
導向、過期／缺 Cookie、舊 URL/localStorage Token 清除、無 Bearer 自動傳送及惡意 redirect。
這不代表 Vercel/LINE 正式設定、真實手機或歷史 Token 影響已完成驗收。

## AI-01 / AI-02：未驗收入口的暫停與設定盤點

`NOMICA_AI_MODE`、`NOMICA_LINE_MODE` 預設 `disabled`。目前僅另允許
`synthetic`，且必須是明確的 loopback development/testing；公開環境不能藉旗標
開啟未完成的 AI。synthetic 只供合成資料與替身流程，仍禁止共用 Adapter 呼叫
雲端模型，也不建立持有正式 Key 的 Gemini client。

- Web `/api/ai/parse` 停用時先驗證身份，再回 503 `AI_DISABLED`，不解析或新增 event。
- `/api/capabilities` 回報可用入口且不快取；前端預設關閉 AI，手動及 QR 仍可操作。
- LINE 停用時仍驗簽；有效 delivery 回 200，不查 profile、不存 inbox/draft、
  不處理文字、選單或 postback、不回覆訊息、不改帳務。這是暫停整個互動入口；
  LINE Login 不受此設定影響。
- Provider/LINE SDK 例外只記型別，不記原文、Token 或完整回應。

這是 S1 的 containment，**不是**共用額度、預算 Reservation、即時 Kill Switch
或 Usage 帳本。對外啟用仍須另完成 G-AI，不能只把模式改名為 public。
未來要恢復 LINE 查詢或選單，也須明確開放並驗收，而不是任意繞過停用分支。
既有解析歷史未在本批刪除，其保存及資料控制仍接 S5。

2026-10-21 本機唯讀盤點：Backend `.env` 存在 Key（未輸出），目前 Git 索引
沒有 `.env`／`frontend/.env.local`，現有 refs 中 `.env` 路徑沒有歷史 commit；
目前 tracked files 沒有匹配 Google Key 格式。這不是完整秘密掃描或未洩漏保證。
正式 Project/Billing/Tier、配額、Spend Cap、Auto-reload、Key 限制、其他 Key
與實例的用量都尚無後台證據；AI-02 的正式環境部分保持待確認，未變更計費或輪替 Key。
