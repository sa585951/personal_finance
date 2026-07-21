# Phase 5.5 Roadmap

Phase 5.5 是 Phase 5 MVP 可用性初步通過後的收斂階段。此階段不追求大功能堆疊，而是驗證使用者是否有理由持續打開 Nomica，並降低日常記帳、帳戶核對與旅行支出追查的操作摩擦。

目前狀態：Phase 5.5 已完成；Phase 6.1 到 Phase 6.7 第一版與最終回歸已完成。

## 目標

- 提升日常操作效率，讓使用者更快完成記帳與查帳。
- 建立回訪理由，讓首頁、LINE 與帳戶頁提供使用者每天或每週想看的資訊。
- 收集留存訊號，判斷 Nomica 的核心亮點是否在 AI 快速輸入、旅行分帳、帳戶追查或預算提醒。
- 進行小幅 component 化與 UI 穩定，避免 Phase 6 前累積過多重複畫面邏輯。

## 優先方向

### 1. 帳戶活動追查與信用卡核對

- 已強化單一帳戶近期活動，支援快速檢查該帳戶的收入、支出、轉入與轉出。
- 讓信用卡可作為支出連結帳戶，並能追查哪些支出已記錄。
- 已加入帳戶活動篩選：全部 / 收入 / 支出 / 轉帳。
- 已讓帳戶活動中的收支與轉帳可銜接既有編輯 / 刪除流程。
- 已修正 LINE 快速記帳與 Web 編輯之間的帳戶連動一致性，避免指定帳戶扣款後，Web 端顯示為不連動帳戶。
- 帳戶提示匹配已適用所有帳戶類型；同機構不同帳戶會優先依完整名稱與上下文匹配，泛稱不應任意抓第一筆。

### 2. LINE / AI 快速記帳優化

- 優先修正 AI parser 的高頻錯誤，例如備註誤填、分類不準、帳戶提示不明確。
- LINE help 與回覆卡片維持與 Web 現行功能一致。
- 已統一 LINE help 與 Web AI 快速輸入的高頻句型，並補上補記日期、帳戶提示與旅行帳本請回 Web 使用的說明。
- 已將投資投入成本導向帳戶互轉與投資類型帳戶，不再作為一般支出分類。
- 已新增「工作」支出分類，用於公司代墊與工作相關支出。
- 觀察 AI parse event 的 `success`、`confirmed`、`failed`，判斷 AI 是否真的降低操作成本。
- 後續統一處理顯示時區：目前 LINE 回覆先以台灣時間顯示，MVP 完整後再改為依使用者或旅行帳本 timezone 顯示。

### 3. 預算超支提醒

- 已補上預算頁的超支提醒卡片，讓使用者不用進入每個分類才知道哪裡超支。
- 優先使用既有預算摘要資料，不新增複雜通知系統。
- Phase 5.5 只做 Web 內提示，LINE 主動推播留到後續評估。

### 4. 首頁資訊可讀性與每日打開理由

- 保留本月結餘、收入、支出與收入/支出比例。
- 避免使用者看不懂的裝飾型圖表；任何圖表都需要文字提示說明資料意義。
- 已加入今日 / 本週摘要與首頁輕量預算警示。
- 後續可評估加入近 7 日支出節奏或待核對帳戶提醒。

### 5. 小幅 component 化與 UI 穩定

- 優先抽出已穩定且重複出現的 UI 區塊，例如帳戶活動、區塊標題、展開/收合列表 footer。
- 不進行整頁大重構，不改資料流，只降低維護成本。
- 每次 component 化都需保持原有互動與文案不變。

### 6. 使用者留存訊號

- 觀察朋友測試後的使用頻率與回饋，不把低頻率直接視為失敗。
- 優先詢問未持續使用原因：沒有記帳習慣、操作仍太麻煩、回饋不夠有感，或功能不符合痛點。
- 以少量問題驗證：AI 是否吸引人、LINE 是否順手、帳戶核對是否有價值、旅行帳本是否比現有工具更貼近需求。

## 不納入本階段

- 完整投資頁。
- 券商 API、即時市值或投資績效分析。
- 原生 iOS App。
- Google / Apple Login 完整商品化。
- 大型 UI 重設計。
- 主動推播通知與付款催收。
- 每位旅行成員各自決定是否把同一帳本計入自己的日常統計。

## 移入 Phase 6 的項目

- 每位旅行成員各自決定是否把同一旅行帳本計入自己的日常統計。
- 外部旅伴與真實登入使用者的安全合併流程。
- iOS 主畫面 PWA / 原生 App 登入策略。
- Google / Apple Login 與 LINE 加綁策略。
- 完整 timezone 顯示模型。
- 自動匯率 API、旅行分類預算與進階旅行報表。
- 投資 / 資金分配獨立頁，仍維持投入成本與資金流向定位，不做券商串接或即時市值。

## Phase 6 第一輪收尾判斷

Phase 6 第一輪已完成的範圍是：

- TripMember 個人月報偏好與旅行分攤統計口徑。
- Nomica Insights 首頁狀態中心。
- 預算頁本月控制狀態整理。
- 收支頁快速輸入、紀錄列表、支出分析與收入來源核對整理。
- LINE / AI 高頻操作的低風險 bug 修補與文案收斂。

以下項目屬於 Phase 6 候選或後續基礎能力，尚未完成但不阻塞第一輪收尾：

- 外部旅伴與真實登入使用者的安全合併流程。
- iOS PWA / 原生 App 登入策略。
- Google / Apple Login 與 LINE 加綁策略。
- 完整 timezone 顯示模型。
- 自動匯率 API、旅行分類預算與進階旅行報表。
- 投資 / 資金分配獨立頁。

Money Flow 已移到 Phase 7；Purpose Model 已移到 Phase 8。

## Phase 6 建議優先順序

1. TripMember 個人月報偏好與旅行分攤統計口徑。
2. Nomica Insights 首頁狀態中心。
3. 預算頁、收支頁與 LINE / AI 高頻操作收斂。
4. 正式登入策略與 provider 加綁。
5. 完整 timezone 與匯率策略。
6. Money Flow 資金流向圖。
7. 投資 / 資金分配獨立頁。
8. iOS / App 化。

## Phase 6 第一輪：Nomica Insights

- 首頁新增 `Nomica Insights` 狀態中心，回答「我現在需要注意什麼？」。
- V1 只做已知事實提醒，不做推測提醒、不新增 schema、不做信用卡到期日或目的分類。
- 目前提醒已收斂為三層：需要處理、值得注意、資訊；信用卡負數、預算超支與旅行月報偏好未決定會優先顯示。
- Money Flow 移到 Phase 7；Purpose Model 移到 Phase 8。

## Phase 6.1：TripMember 個人月報偏好

- 旅行是否納入月報改由每位登入成員自行決定，不再由整本旅行帳本決定所有人。
- `pending` 與 `exclude` 不納入月報；只有 `include` 納入。
- 多人旅行納入個人月報時，只使用該成員自己的分攤金額，不使用整筆旅行支出。
- 外部旅伴沒有個人月報偏好，不影響登入使用者的月報統計。

## Phase 6.2 / 6.3：預算頁與 Insights 收斂

- 預算頁整理為本月預算控制狀態，補上總預算、已花費、剩餘、使用率、快用完與未設定預算支出。
- 首頁 `Nomica Insights` 聚焦跨模組狀態入口，不取代預算頁、收支頁或旅行頁的完整內容。

## Phase 6.4：收支頁資訊架構與收入核對

- 收支頁快速輸入依收入 / 支出模式切換提示詞與範例，減少使用者在收入頁看到支出句型的混淆。
- 手動新增表單預設收合，AI 解析套用或手動新增時才展開，維持「AI 填表、使用者確認」的操作模型。
- 最近紀錄、支出分析與收入核對區文案收斂，讓使用者更清楚每個區塊回答的問題。
- 收入模式補上收入來源核對，以總額卡、來源分布條與來源清單呈現本月收入來源，不新增 API 或複雜圖表。
- LINE 收入確認卡修正中文 / 英文交易類型判斷，並在收入 / 支出成功卡補上類別顯示。

## Phase 6.5：旅行頁狀態中心

- 旅行頁新增 `旅行狀態中心`，集中顯示個人月報偏好、分攤完整度、待收待付與類別比例狀態。
- 每個狀態卡可直接帶使用者前往對應區塊，例如交易、分帳或類別比例摘要。
- 本輪沿用既有旅行 overview、transaction splits 與 settlement suggestions，不新增 API、不新增 migration。
- 旅行支出類別改用 API 的 category kind 篩選，只顯示 `expense` 與 `both`，避免收入類別混入支出表單。
- 記帳提醒通知先列為後續策略題，不在 Phase 6.5 直接實作推播或 LINE 主動提醒。

## Phase 6.6：收支頁帳戶流向分析

- 收支頁新增支出 `付款來源分析`，回答「同樣是支出，從哪些帳戶類型付出去」。
- 收入頁新增 `入帳帳戶分析`，回答「收入進到哪些帳戶類型」。
- 分析依帳戶類型與幣別分組；多幣別不硬加總，避免在沒有匯率模型前產生錯誤總額。
- 未連動帳戶會獨立列為 `未連動帳戶`，協助使用者發現需要補連動的交易。
- 本輪由 `/api/transactions` 直接回傳 `account_type`，不新增 endpoint、不新增 migration。

## Phase 6.7：資產頁帳戶健康度

- 資產頁新增 `帳戶健康度`，讓使用者一進帳戶頁先看到需要留意的帳戶狀態。
- V1 只使用系統已知事實：信用卡負數、非信用卡負數、零餘額帳戶與未追蹤餘額帳戶。
- 不做信用卡繳款日、不做低水位門檻、不做推測型提醒；這些列入後續帳戶健康度進階版本。
- 本輪沿用既有 `/api/assets` 資料，不新增 API、不新增 migration。

## Phase 6 最終回歸

2026-06-25 已完成：

- 前端 `npm run build` 通過。
- 前端 `npm run lint` 通過。
- 後端完整 pytest：`78 passed, 6 skipped`；skip 項目為需明確開啟的資料庫 smoke 測試。
- 資料庫 schema smoke test：`4 passed`。
- 首頁、收入 / 支出、預算、旅行與帳戶頁均可載入，瀏覽器未出現 JavaScript runtime error。
- 390px 手機寬度下主要頁面沒有水平溢出。
- 收支編輯表單第一次點擊即可帶入資料；旅行支出表單不再顯示收入類別。

Phase 6 第一版可判定完成。正式登入與 provider 加綁、完整 timezone、匯率、Money Flow、投資獨立頁與 iOS App 仍屬後續規劃，不列為本次回歸失敗。

## Phase 7 前維護整理

- 前端 router 改為 route-level lazy loading，移除單一 bundle 超過 500 KB 的 build warning。
- LINE Messaging API 改用 `line-bot-sdk` v3 parser、Messaging API、`ReplyMessageRequest` 與 `PushMessageRequest`。
- Flex 卡片內容維持既有 JSON 與視覺，透過專案內部 adapter 建立 v3 `FlexMessage`。
- 新增 v3 reply、push 與 webhook parser 測試；完整後端測試通過且不再出現 LINE SDK deprecated warnings。
- 正式環境仍需以 LINE 官方帳號完成文字訊息、postback、reply 與 push 的實機驗收。

## Phase 7.1：Nomica 主帳號與正式 Session 地基

- Nomica `users.id` 是主帳號；LINE、Apple、Google 都只是可綁定 identity provider。
- 第一版採 session-backed JWT：JWT 是前端憑證，`auth_sessions` 是後端有效性來源；JWT 與 session 固定 30 天同時過期。
- LINE Login 保留為登入與快速記帳入口，避免破壞目前 Web / LINE 測試流程。
- 新增帳號設定頁雛形，顯示 LINE 已啟用、Apple / Google 尚未啟用。
- 本輪不做 refresh token、silent refresh、sliding session、cookie-only session、正式 Apple / Google OAuth 或裝置管理 UI。
- Phase 7.2 優先接 Apple Login；Phase 7.3 再接 Google Login；帳號合併採登入後手動加綁，不使用 email 自動合併。

## Phase App 0：iOS 原生殼 Prototype

- 新增 `ios/Nomica` SwiftUI prototype，先作為 iOS 學習與 API 可行性驗證。
- 第一版只做本地 dev API 串接：登入狀態測試、首頁摘要、收支列表與帳戶列表。
- 不做 Apple Login、Google Login、Keychain、TestFlight、Push 或完整新增編輯流程。
- Web / LINE 仍是現階段主要測試入口；iOS 先驗證原生 App 架構是否成立。

## Allocation 0：Asset Allocation Domain 定案

- Asset Allocation 是 Web、LINE 與 iOS 共用的產品 Domain，不歸類為 iOS 專屬功能。
- Account 回答資金位置，Portfolio 回答配置策略，Holding 回答持有標的，Bucket 回答資金用途；四者不可混用。
- Recorded Cost 與 Portfolio Snapshot 分離；Snapshot 是使用者在特定日期手動建立的完整 Portfolio 快照，不是即時行情。
- Allocation V1 不把 Snapshot value 與既有 Account balance 相加，避免資產總額重複計算。
- 新增資金配置只做確定性試算，不提供賣出、選股、市場預測或交易建議。
- Bucket / Purpose Model 延後到 Allocation 2。
- 詳細 Domain、驗證規則與 API 草案記錄於 `docs/asset-allocation-domain-plan.md`。

## Allocation 1A：Asset Allocation Schema 地基

- 新增 Portfolio、Holding、Recorded Cost Entry 與完整 Portfolio Snapshot 的資料結構。
- V1 僅支援 investment Account，且 Portfolio 維持單一基準幣別。
- Holding 目標比例可先保存草稿；正式配置比較與新增投入試算才要求合計 100%。
- 一筆既有帳戶轉帳可分配到多個 Holding；完整 ownership 與總額驗證排入 Allocation 1B API/service。

## Phase 5.5 通過標準

- 使用者能更快完成日常記帳與帳戶核對。
- 首頁與帳戶頁資訊更容易理解，沒有明顯「看得到但看不懂」的圖表。
- LINE / AI 快速輸入至少能成為測試使用者願意再試一次的入口。
- 預算超支狀態可被快速看見。
- 主要畫面經過小幅 component 化後，沒有破壞既有功能與測試流程。

## 收尾結論

- Phase 5.5 第一輪可判定完成，已涵蓋首頁回訪理由、預算可見性、帳戶核對、LINE / AI 輸入一致性與近期高風險 bug 修正。
- Phase 6.1 到 Phase 6.7 第一版與最終回歸已完成，目前可進入真實使用觀察與下一階段討論；若後續測試發現阻塞級 bug，仍先以低風險修補處理。
- 此階段不是市場驗證完成，使用頻率、留存與付費價值仍需後續資料驗證。
