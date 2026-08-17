# Nomica Product Roadmap

## 狀態

- Roadmap 版本：M0 至 M9
- 生效日期：2026-08-17
- 目前 Milestone：M0 Finance Contract 與產品量測基準
- M0 完成後第一個程式實作批次：M1A Mobile UX Bug 修正

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

- 修正 horizontal overflow、標題與 bottom navigation 裁切、固定寬度、spacing、sheet/modal 捲動。
- 驗收 390、430、768px，不以縮小字體掩蓋問題。

### M1B Trip Route 拆分

- `/trips`：Upcoming、Ongoing、Past 列表。
- `/trips/:tripId`：Overview、Expenses、Split、Members。
- `/trips/invite/:token`：保留邀請流程。
- 逐步拆分既有大型 `TripsView.vue`，不先重構後端。

### M1C Universal Add V1

- 統一「一句話或手動輸入 -> Preview -> Confirm」。
- AI 信心不足時只補缺少欄位。
- Confirm 需具備防重複送出行為。

### M1D Home 與 Analysis V1

- Home 只回答本月狀態、待處理事項與下一個動作。
- `/analysis` 搬移既有 summary、category、trend、payment source、budget 與 basic trip summary。
- Bottom Navigation：首頁、紀錄、旅行、分析、帳戶。

## M2 PWA Alpha

- 以 5 至 10 位非開發者驗證登入、第一帳戶、第一交易、旅行、邀請、shared expense、share、group settlement 與個人月報。
- 此時 Settlement 仍為 group-only；UI 不得暗示會自動異動私人帳戶。
- Alpha 後只修高頻阻塞，不立即擴充功能。

## M3 Ledger Correctness

- M3A：`account_balance_anchors`。
- M3B：`account_adjustments`，手動校正不算收入支出。
- M3C：`settlement_account_entries`，群組結算與私人帳戶 posting 分離並具冪等性。
- M3D：CLI reconciliation tool，比對 Expected Balance 與 stored balance。
- M3E：legacy goals 與舊 schema 使用情況收斂。
- 月報不得把 Settlement、Transfer、Adjustment 算成收入支出。

## M4 Travel Product

- 只有 PWA Alpha 資料支持後才做。
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
