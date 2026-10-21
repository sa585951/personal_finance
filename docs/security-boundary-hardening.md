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

## DEP-01：相容依賴更新與剩餘風險

2026-10-21 以 npm registry 重新盤點，更新 axios 至 1.20.0、Vue 至
3.5.44、Vite 至 7.3.7，並更新既有相依範圍內的 transitive packages。
保留現有主版本與 ESLint 設定，未使用 `audit fix --force`、強制 overrides
或執行套件安裝 scripts。確切版本以 `frontend/package-lock.json` 為準。

| 範圍 | 更新前 | 更新後 |
| --- | --- | --- |
| 完整 lockfile audit | 20（14 high、5 moderate、1 low） | 7 moderate；無 high / critical |
| 更新後 `npm audit --omit=dev` | 本批未另保存更新前分類數量 | 0 |

剩餘 7 項是兩條開發工具相依鏈的統計，不是 7 個獨立執行期漏洞：

- `eslint-plugin-vue@8.7.1 → postcss-selector-parser@6.1.5`：
  [selector 解析 CPU 耗盡](https://github.com/advisories/GHSA-rj75-hqrm-r3gf)，
  audit 指出修補範圍為 7.1.6 以上，超過既有父套件要求的 6.x。
- `eslint / @eslint/eslintrc → js-yaml → argparse → sprintf-js@1.0.3`：
  [不受限 precision 的 DoS](https://github.com/advisories/GHSA-hp3w-g68c-fv3c)。
  audit 建議的完整修復包含 ESLint 主版本更新，需獨立遷移設定與回歸。

本批未發現這兩個套件由 production runtime dependencies 引入；此結論只限
npm 相依分類，不代表所有 build 工具都不會進入產物。已知可達面是處理原始碼的
lint / 工具鏈；對不可信 PR、CSS 或格式字串的實際 exploit 未在本批重現。
後續以獨立工作升級 ESLint / Vue lint plugin 並驗證規則相容性；CI 不向不可信
程式提供正式憑證，執行環境應保留逾時及資源限制。不得把 audit 歸零作為全面重構理由。

## 本批本機驗證證據與發布限制

- Backend：465 passed；包含真實隔離 PostgreSQL、多連線 state 競爭、
  migration 空庫及既有 0017 含帳務資料升級，以及原有帳務／發票／LINE 回歸。
- Frontend：`check:styles`、`lint`、production `build` 通過；正式 build
  若設定 `VITE_DEV_AUTH_BYPASS=true`，已確認會拒絕建置。
- Chrome `test:ui`：五尺寸、深淺色、惡意對話框內容、Cookie 導向及 AI
  停用時手動記帳流程；API 與相機為替身，不等於實機／正式 API 驗收。
- 另以最終 production build、本機 HTTPS、真實 Flask API 與本批專用
  PostgreSQL 驗證 Cookie 登入、導向、登出撤銷及重新載入。
  LINE 授權／token exchange 仍為替身，未呼叫正式 LINE 或 Gemini。
  驗證 Cookie 的 HttpOnly / Secure / SameSite=Lax、URL 與 localStorage
  不留 Token、登出後 `/api/auth/me` 回 401；該合成使用者未建立財務交易。

測試 DB 是本批新建的 tmpfs PostgreSQL container，未掛載既有資料卷；
測試連線另以 host / port / database allowlist 拒絕其他 PostgreSQL 目標。
沒有修改正式 DB、正式環境變數、Provider 設定或既有使用者財務資料。

這些證據只支持本機修補，不宣告 S1 正式部署或 G1 通過。
公開前仍須完成上方 staging 同源代理／真實 LINE callback 驗收、手機 PWA
Cookie 與相機實測、正式 Key / Billing 證據及相應發布門檻。
S2 帳務併發、S3 匯率／月報、S4 重試與核心流程、S5 真實資料門檻及
S6 正式產品交付順序維持不變。
