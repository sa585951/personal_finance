# Deployment Checklist

更新：2026-11-10。僅規劃與驗收清單，不是已部署證明。
最新設定契約以 `docs/security-boundary-hardening.md` 為準。

## 本機到 staging

1. 先確認目標環境、DB 身分與備份；核對實際 migration head。
   本地目前 chain head 為 `20261111_0022`，不可直接拿測試 runner 連 staging／production。
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
   月上限預設 5 USD，每人每日 30 次（`NOMICA_LINE_AI_DAILY_PER_USER` 可調）；設
   `NOMICA_ADMIN_LINE_USER_ID` 可收到 80% 用量通知，見 [LINE AI 試用](line-ai-pilot.md)。Web 一句話記帳只用本機規則；
   Web AI 維持 `NOMICA_AI_MODE=disabled`。
7. 憑證只存部署平台秘密設定；範例可版控，真實 `.env`、DB dump、Token 不可版控。
   依需求配置 JWT、DB、LINE Login 憑證；停用 AI 不需要為了部署加入 Gemini Key。
8. 協調 frontend/backend 版本與回退方案。回退不得直接刪除 state、命令或去重資料表。
9. 刪除帳號 30 天後的永久清除：`python -m scripts.purge_deleted_users` 預設只試跑並回報筆數，
   加 `--apply` 才寫入。建議每天排程一次（例如 Render Cron Job，指令同上並帶 `--apply`），
   沒有到期的資料時不會刪除任何東西。同一個排程也會刪除超過 180 天的首頁點擊等量測事件。
   清除後只能從資料庫備份還原。

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

## 封閉測試

四週封閉測試期間的準備、例行檢查、停用與回退。

### 開始前（一次）

| 項目 | 怎麼做 | 完成 |
| --- | --- | --- |
| 資料庫備份 | Supabase：確認自動備份已開啟，並在升級前手動建立一次備份 | [ ] |
| Migration | `DATABASE_URL='…' alembic current` 確認版本，再 `alembic upgrade head`，結果應為 `20261111_0022 (head)` | [ ] |
| 部署 | Render 部署對應的 main；Vercel 前端同步 | [ ] |
| 環境變數 | `GEMINI_API_KEY`、`NOMICA_LINE_AI_PAID_PROJECT_VERIFIED=true`；建議設 `NOMICA_ADMIN_LINE_USER_ID`（80% 用量通知）；`NOMICA_LINE_AI_DAILY_PER_USER` 不設即每人每日 30 次 | [ ] |
| 清除排程 | 每天執行 `python -m scripts.purge_deleted_users --apply`（例如 Render Cron Job，使用同一組 `DATABASE_URL`） | [ ] |
| 政策頁 | `frontend/src/constants/policies.js` 的營運者與聯絡方式改為實際內容 | [ ] |
| 上手說明 | 填好下方附錄的 `〔〕` 後寄給試用者 | [ ] |
| 實機驗收 | 見下方清單 | [ ] |

### 實機驗收

用兩個 LINE 帳號（A、B）：

- [ ] A、B 各自用 LINE 登入 Web，首頁看到的是各自的帳本
- [ ] Web：一句話「午餐 120」填入後記下，餘額正確
- [ ] LINE：「午餐 120」→ 選帳戶（翻頁、打字選擇各一次）→ 確認，只入帳一次
- [ ] LINE：規則看不懂的句子 → 出現同意說明 →「同意 AI」→ 重傳 → 草稿 → 確認
- [ ] LINE：「撤回 AI」後，同一類句子不再送 AI
- [ ] A 建立旅行並邀請 B；B 加入後兩人都能看到同一筆旅行支出，分帳結果一致
- [ ] iPhone 與 Android：掃描發票 QR、圖片備援、同一張發票重掃不重複記帳
- [ ] 「我的 → 帳號與隱私」：匯出資料可開啟

### 每週例行

```bash
DATABASE_URL='…' python -m scripts.beta_metrics --weeks 4
```

看四件事：

1. `people_with_2plus_days`：每週記帳至少兩天的人數
2. `web_sentence_unchanged_ratio` 與 `line_drafts`：一句話記帳是否準確
3. `new_people_via_trip_invite`：旅行邀請帶來的新使用者
4. `line_ai_usd_this_month`：AI 費用

同時整理本週回報的問題，標記為「帳務錯誤」「看不懂」「想要的功能」。帳務錯誤當天處理。

### 出問題時

| 狀況 | 立即處理 |
| --- | --- |
| LINE AI 回覆異常或費用異常 | 停用 AI：在資料庫執行 `UPDATE line_ai_control SET enabled = false WHERE id = 1;`（立即生效，改回 `true` 恢復）。或把 `NOMICA_LINE_AI_MONTHLY_USD` 設為 `0` 後重新部署。規則記帳不受影響 |
| LINE 回覆整體異常 | 設 `NOMICA_LINE_MODE=disabled` 後重新部署，LINE 停止回應，Web 不受影響 |
| 新版本有問題 | Render 回退到上一個部署；Vercel 回退到上一個 Production 部署。0021、0022 只新增欄位與資料表，回退程式時不需降版資料庫 |
| 帳戶餘額看起來不對 | 唯讀檢查：`python -m scripts.reconcile_accounts --fail-on-issues`；不要直接改資料庫餘額 |
| 試用者要刪除資料 | 請本人在「我的 → 帳號與隱私」刪除帳號；30 天後由清除排程永久刪除 |
| 資料毀損 | 從 Supabase 備份還原到新資料庫、核對後再切換；清除排程刪掉的資料只能從備份找回 |

### 結束時

- 匯出最後一次 `beta_metrics`，整理訪談與回報。
- 決定 Web Gemini、iOS 與收費的下一步（見 [product-roadmap.md](product-roadmap.md)）。

## 附錄：給試用者的上手說明

可直接轉貼給受邀試用者。`〔〕` 內的內容由營運者在寄出前填好。

### 開始使用（約 3 分鐘）

1. 加入 LINE 官方帳號：〔官方帳號連結或 QR Code〕
2. 用手機或電腦開啟 〔Nomica 網址〕，按「使用 LINE 繼續」登入。之後在 LINE 記的帳都會記到這個帳號。
3. 在「我的 → 帳戶」建立常用帳戶，例如現金、銀行、信用卡。
4. 手機可以把網頁加到主畫面，用起來像 App：
   - iPhone（Safari）：分享 → 加入主畫面
   - Android（Chrome）：選單 → 加到主畫面

### 怎麼記帳

**在 LINE 說一句話**，Nomica 會整理成草稿，你按「確認」才會入帳：

- 「午餐 120」
- 「昨天跟同事吃晚餐 刷玉山卡 450」
- 「計程車 280 現金」

需要選帳戶時，可以按按鈕，也可以直接回覆帳戶名稱（信用卡可簡稱「玉山卡」）。

規則看不懂的句子，可以交給 AI 解析。第一次使用時 Nomica 會說明資料怎麼處理；回覆「同意 AI」才會開啟，回覆「撤回 AI」可隨時關閉。AI 每人每天最多 30 次，用完時仍可用「午餐 120」這種格式記帳。

**在網頁記帳**：按下方的「＋」，在上方輸入一句話後按「填入」，或直接填表單。

**旅行**：在「旅行」建立一趟旅行，從「旅伴」邀請同行的人。旅途中按「記一筆旅行支出」，結束後在「分帳」查看誰該給誰多少。

### 請不要輸入

卡號、密碼、驗證碼、身分證字號。記帳只需要品項、金額和帳戶。

### 遇到問題或想法

- 回報方式：〔例如 LINE 群組、表單連結〕
- 回報時請附上：發生的時間、在哪個頁面或 LINE、你做了什麼、看到什麼畫面（截圖最好）。
- 每週會有一則簡短問題，請花一分鐘回覆。

### 你的資料

- 測試期間免費。
- 隨時可在「我的 → 帳號與隱私」下載資料、登出所有裝置或刪除帳號。
- 詳細說明見網頁上的「隱私權政策」與「服務條款」。
