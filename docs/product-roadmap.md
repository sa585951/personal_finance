# Nomica Product Roadmap

## 狀態

- Roadmap 版本：M0 至 M9
- 生效日期：2026-08-17
- 目前 Milestone：M3 Ledger Correctness 第一輪完成；M2 PWA Alpha 以有限證據收尾，解除後續 Web 開發關卡
- 目前工作批次：發票掃描記帳 V1；API contract 基線已建立。支援台灣電子發票左側 QR、跨來源精確去重、人工確認候選，以及建立／連結日常支出；部署需先套用 `20261008_0016`。
- 帳期與共用分頁批次狀態：本地第一版、migration chain、DB smoke 與 390／430px 操作驗收已完成；正式環境仍須套用 `20260925_0015` 並做部署後驗收，不視為已上線

舊有 Phase 1 至 Phase 7、Phase App 與 Allocation 文件保留為歷史開發紀錄。新工作一律使用本文件的 Milestone 命名，避免同時維護兩套進度語言。

## 已完成基線

進入 M0 前，專案已具備以下能力：

- Web、LINE 的日常收入與支出記錄。
- 帳戶餘額連動、帳戶互轉、信用卡負數與帳戶活動追查。
- 旅行帳本、多人邀請、分攤、群組結算與個人月報偏好。
- 預算、首頁 Insights、收支分析與手機優先 UI 第一輪。
- Session-backed JWT 與 Nomica user 主帳號地基。
- Asset Allocation 1A 至 1C：schema、API 與 Web 操作。
- iOS read-only prototype：session gate、首頁、收支、帳戶與 API 錯誤狀態。

iOS Prototype 在此暫停。`KeychainStore` 目前是尚未接入 `AppSession` 的探索草稿，不視為正式 Auth Foundation 完成；正式整合移至 M6A。

## 執行原則

1. 每次只交付一條可驗收的垂直流程。
2. UX 重組期間不修改財務計算邏輯。
3. Ledger migration 採新增、切換、驗證、停用舊路徑，不直接破壞既有資料。
4. 每個 Milestone 結束必須維持後端測試、前端 production build 與既有日常／旅行／分帳回歸通過。
5. 手機畫面需檢查 390、430、768px，且 `document.scrollWidth <= viewport width`。
6. PWA Alpha 驗證操作可發現性；PWA Beta 驗證 Shared Expense 到 Personal Finance 的財務語意。

## M0 Finance Contract 與產品量測基準

狀態：第一版完成（2026-08-17）。Finance Contract、Balance／Settlement Ownership Contract、Product Event Taxonomy 與 characterization tests 已建立；完整後端回歸為 102 passed，前端 production build 通過。

### 目標

先固定財務語意與產品事件，避免 Web、LINE、iOS 各自解讀。

### 交付

- `docs/finance-contract.md`
  - 定義 Payment、Expense、Share、Receivable、Payable、Settlement、Transfer、Account Movement、Adjustment、Balance Anchor。
  - 固定 `Payment != Expense`、`Settlement != Income / Expense`、`Transfer != Income / Expense`。
  - 定義 Balance Contract 與 Settlement Ownership Contract。
- `docs/product-event-taxonomy.md`
  - 定義 signup、第一帳戶、第一交易、旅行、邀請、shared expense、settlement 與月報事件。
  - Analytics 禁止帶自然語言原文、交易備註、帳戶名稱、精確金額、Email 或第三方 identity。
- Characterization tests
  - 先鎖定現有財務行為，不在 M0 改 schema 或 UI。

### 驗收

- Finance Contract 案例逐一確認。
- 現有行為與未來 Ledger 行為有明確區分。
- 現有測試維持通過。

## M1 Minimum Product UX

### M1A Mobile UX Bug

狀態：第一版完成（2026-08-17）。

- 修正 horizontal overflow、標題與 bottom navigation 裁切、固定寬度、spacing、sheet/modal 捲動。
- 驗收 390、430、768px，不以縮小字體掩蓋問題。
- 第一輪已完成六個主要頁面的 390、430、768px overflow audit，並修正 bottom navigation 與 Dev 使用者選單重疊；目前各寬度皆無水平溢出或導覽裁切。

### M1B Trip Route 拆分

狀態：第一版完成（2026-08-19）。

- `/trips`：Upcoming、Ongoing、Past 列表。
- `/trips/:tripId`：Overview、Expenses、Split、Members。
- `/trips/invite/:token`：保留邀請流程。
- 逐步拆分既有大型 `TripsView.vue`，不先重構後端。
- 第一輪已將 `/trips` 與 `/trips/:tripId` 分離，新增獨立 `TripListView.vue`，並保留詳情頁原有支出、分帳、旅伴與結算行為；列表分期分類與詳情內部 component 化可在後續 UX 維護持續收斂。

### M1C Universal Add V1

狀態：第一版完成（2026-08-20）。

- 統一「一句話或手動輸入 -> Preview -> Confirm」。
- AI 回報缺少必要欄位時，只展開需要補完的欄位；不建立 parser 未提供的 confidence 數值。
- Confirm 需具備防重複送出行為。
- 日常收支統一由 `/add` 新增；旅行支出維持旅行詳情內的獨立流程。
- `POST /api/transactions` 以 optional `client_request_id` 支援順序與併發重送，帳戶餘額只異動一次。
- 交易列表使用 cursor pagination，最近紀錄與月份查找目前每頁 20 筆；月度分析以分頁方式取得完整月份資料。
- 未刪除帳務資料不因列表分頁而刪除。軟刪除後 30 天僅代表符合永久清理資格，目前未宣稱已有自動 purge worker。
- 本批部署順序固定為 Alembic migration `20260819_0010`、backend、frontend。

### M1D Home 與 Analysis V1

狀態：第一版完成（2026-08-20）。

- Home 只回答本月狀態、待處理事項與下一個動作。
- `/analysis` 搬移既有 summary、category、trend、payment source、budget 與 basic trip summary。
- Bottom Navigation：首頁、紀錄、旅行、分析、帳戶。
- 首頁保留本月月報與 Nomica Insights；今日／本週摘要、旅行狀態與近期紀錄不再重複佔用首頁。
- `/transactions` 只保留收入／支出紀錄、月份查找、分批載入、編輯與刪除。
- `/analysis` 提供總覽、支出與資金來源三個檢視，月份與「含旅行／日常」口徑同步影響摘要、分類與預算狀態。
- 預算與旅行在 Analysis 僅提供摘要與專頁入口，不取代原本管理頁。
- 日常新增入口改放在首頁與紀錄頁標題列，移除會遮擋內容與帳號選單的全域浮動按鈕；旅行支出仍留在旅行詳情。
- 本批只調整 frontend 資訊架構，沒有 migration 或後端財務計算異動。

## M2 PWA Alpha

狀態：有限證據收尾（2026-09-25）。已有試用者提出問題並促成後續修正，但沒有完整的 5 至 10 位非開發者分段測試、完成率與留存紀錄；不宣稱原訂 Alpha 門檻正式通過。使用頻率不固定不再無限期阻擋後續 Web 產品化。

- 原訂以 5 至 10 位非開發者驗證登入、第一帳戶、第一交易、旅行、邀請、shared expense、share、group settlement 與個人月報；原目標與未驗證項目見 `docs/m2-pwa-alpha-plan.md`。
- Group Settlement／部分還款只更新群組分帳狀態，不自動異動私人帳戶；使用者可另外為自己的一側選擇同幣別帳戶入帳或扣款。
- 後續 Web 工作改以已知使用者問題安排可獨立驗收的小批次；下一批為信用卡帳期資訊，不將帳戶負餘額誤稱為本期應繳。
- M2 有限證據收尾不代表完成財務 reconciliation、留存或市場驗證；iOS 正式開發仍依後續 Web／PWA 產品與財務語意驗證結果決定。

## M3 Ledger Correctness

狀態：M3A 至 M3E 第一版完成（2026-08-21）。

- M3A：`account_balance_anchors`。已為新帳戶建立初始 anchor，migration 也會以既有快照回填 legacy anchor，不猜測 anchor 前的歷史 movement。
- M3B：`account_adjustments`。帳戶餘額校正會保存調整前後金額、delta、原因與時間，並與 `accounts.balance` 在同一 DB transaction 更新；Adjustment 不算收入支出。
- M3C：`settlement_account_entries` 已完成第一版。群組結算與私人帳戶 posting 分離；付款方與收款方只能操作自己的同幣別帳戶，重送不重複異動，反轉只執行一次。有 active 私人 posting 時禁止 owner 直接撤銷群組結算。
- M3D：`account_movements` 與 read-only reconciliation CLI 已完成第一版。Transaction／Transfer 新增、編輯與刪除會在同一 DB transaction 留下 append-only movement；CLI 以最新 Anchor 加總 movement、Settlement 與 Adjustment，比對 Expected Balance 與 stored balance，且不會自動修正。
- M3E：legacy goals 與舊 schema 使用情況已完成第一輪收斂。Goals API 現在只保留 authenticated `410 Gone` 相容回應，Web 舊路徑導回 Analysis，LINE Rich Menu 建立腳本不再產生 Goals 入口；legacy table 與資料暫時保留，不執行破壞性 migration。
- 月報不得把 Settlement、Transfer、Adjustment 算成收入支出。
- M3D 的可靠範圍從 `20260821_0013` 建立的 `reconciliation_baseline` 開始；Anchor 前的 legacy 歷史不回推，也不宣稱是完整 Event Sourcing。
- legacy schema 的保留、隔離與後續處理依據見 `docs/legacy-schema-inventory.md`。

## M4 Travel Product

- 只有明確的旅行使用問題或後續驗證資料支持後才做；M2 有限證據收尾不自動啟動 M4。
- 推導 Upcoming／Ongoing／Ended，並依 Trip timezone 計算。
- 增加 explicit closeout 與 final personal cost。
- Active Trip 只做推薦，不直接 commit。

## M5 PWA Beta

- 驗證使用者能理解 Payment、My Cost、待收／待付及 Settlement account movement。
- 達到無重大財務錯誤、語意可理解且有主動回訪訊號後，才投入完整 iOS。

## M6 iOS Vertical Slice

### M6A Auth Foundation

- Sign in with Apple、LINE Login、multi-identity、Keychain、session expiry、logout、revocation 與 401 清除失效 token。
- Identity linking 只允許登入後主動綁定，不依 Email 自動合併。
- 正式版本移除 `X-Dev-User` 與手動 token。

### M6B Mobile Slice

- Login、Home、Quick Add、Transaction list、Trip list/detail、Trip Quick Add、My Cost、Split Summary。
- 第一個 TestFlight 不要求 Asset Allocation、完整 Budget、進階 Analysis 或所有 Trip 管理權限。

### M6C TestFlight

- 驗證首次登入、token 保存、App 重開、網路失敗、session 失效、日常／旅行快速記帳與 decode error。

## M7 LINE Travel Context

- 只有 Beta 證明 LINE 有留存價值才投入。
- 順序為 Active Trip Recommendation、Trip Quick Add、Shared Parse。
- Shared Parse 必須經過 Parse、Preview、Confirm、Commit，不直接 auto-commit 分帳。

## M8 Release Engineering 與 App Store

- Backup、restore drill、migration forward／rollback、structured logging、rate limit、abuse protection、secret rotation、health checks。
- Account deletion、Token revoke、Privacy Policy、Terms、data retention 與 App Privacy 申報。
- 建立並驗證自動 purge、資料匯出與帳號刪除流程；在此之前 `purge_after` 只表示符合清理資格。
- Release build 不得包含 dev auth。

## M9 Plus

- 目前只保留 feature flag／entitlement boundary。
- 取得 4 週留存、AI 成本、Shared/Trip 使用率與付費需求資料前，不做 StoreKit、billing table 或 subscription UI。

## 明確暫緩

- Offline-first sync。
- 自動匯率 API。
- Trip 分類預算。
- Advanced AI Insight 與跨旅行比較。
- Asset Allocation 擴充與 Bucket／Purpose Model。
- Web／iOS 完整 feature parity。
- Microservices。
- Shared Expense auto-commit。
- Goals 復活。

## 執行順序

以下為原訂 Milestone 順序；實際上 M3 第一輪已先完成，M2 則以有限證據收尾。信用卡帳期、共用分頁與 API contract 基線已完成本地第一版，目前進行發票掃描記帳 V1；這些獨立批次不代表 M4 已啟動。發票批次確認、載具同步、OCR 與旅行發票留待獨立批次。

```text
M0 Finance Contract
 -> M1 Minimum Product UX
 -> M2 PWA Alpha
 -> M3 Ledger Correctness
 -> M4 Travel Product
 -> M5 PWA Beta
 -> M6 iOS Vertical Slice / TestFlight
 -> M7 LINE Travel Context (依數據決定)
 -> M8 App Store
 -> M9 Plus (依留存與成本決定)
```
