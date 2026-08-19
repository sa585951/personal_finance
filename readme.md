# Nomica

Nomica 是一個手機優先的個人財務工具，目前整合日常記帳、帳戶、旅行與使用者自行維護的資產配置，協助使用者掌握資金位置與自己制定的配置策略。

本專案一開始是為了讓自己能更方便地記錄日常支出，後續加入了 Web 管理介面、LINE Login、LINE Bot 自然語言記帳、資產、預算與報表等功能。接下來的開發方向會收斂，不再追求全功能理財 App，而是聚焦在自己真正會使用的場景：平常快速記帳，出國時能獨立記錄旅行支出，回來後可換算成本幣並產生結算。

## 專案定位

**Nomica** 的定位是：

> Nomica 是整合記帳、帳戶、旅行與資產配置的個人財務工具，協助使用者掌握資金位置與自己制定的配置策略；不提供行情、選股、交易或買賣建議。

長期內部願景是 Personal Finance OS；產品不取代看盤、券商或完整投資管理 App，而是成為自己真的願意持續使用的財務操作工具。

目前的產品重心：

- 日常收入與支出記錄
- 出國/旅行支出記錄
- 多幣別與匯率換算
- 旅行成員與輕量分帳
- 旅行結算與本幣彙總
- 帳戶與資金流向管理
- 使用者自行維護的資產配置策略（Allocation 1A schema、1B API 與 1C Web 操作完成）
- 手機優先操作體驗
- LINE / Web 兩種快速輸入入口

## 目前進度

目前專案已完成舊 Roadmap 的 Phase 1 至 Phase 7.1、Asset Allocation 1A 至 1C、Phase App 0 的 iOS read-only prototype，以及新 Roadmap 的 M0 Finance Contract、M1A Mobile UX Bug 第一輪、M1B Trip Route 拆分第一版與 **M1C Universal Add V1**。自 2026-08-17 起，後續工作改用 M0 至 M9 Milestone；下一批進入 M1D Home 與 Analysis V1。M1A 已完成六個主要頁面的 390、430、768px overflow audit；M1B 已將旅行列表 `/trips` 與旅行詳情 `/trips/:tripId` 分開；M1C 已建立 `/add` 統一新增入口與交易歷史分批載入。核心流程已可在本地與部署環境操作：

- 日常收入 / 支出可記錄，並可連動帳戶餘額。
- Web 日常收支新增已統一由 `/add` 處理，支援 AI Preview、缺少欄位補完、手動收入 / 支出與防重複送出。
- 收支紀錄預設讀取最近 10 筆，可每次再載入 10 筆或依月份查找；月份摘要與付款來源分析仍取得完整月份資料。
- 帳戶可依銀行、現金、信用卡、電子錢包、預付卡、投資、外部帳戶與其他類型管理，帳戶列表與交易帳戶選擇已依類型分組。
- 帳戶互轉已支援同幣別與跨幣別轉帳；信用卡帳戶允許負數累積，其他帳戶仍保守限制不可為負數。
- 投資類型目前用於資金分配與投入成本紀錄；Asset Allocation 已提供 Portfolio、Holding、投入成本、手動 Snapshot 與新增投入試算，仍不串接券商或即時行情。
- 旅行帳本可建立、切換、封存、軟刪除、復原，並支援每位登入成員自行決定是否納入個人月報。
- 旅行支出可指定付款人、幣別、匯率與是否連動自己的帳戶。
- 若付款人不是目前登入使用者，交易不會連動自己的帳戶，避免未來多人帳本時誤扣他人操作造成的帳戶餘額。
- 旅行支出支援平均分攤與自訂分攤。
- 分帳頁可顯示每位旅伴的已付款、應分攤、待收 / 待付狀態。
- 建議結算可標記為已付款，也可撤銷；結算只影響分帳淨額，不異動帳戶餘額。
- 旅行總覽已區分「我的分攤」、「整團花費」與「待收 / 待付 / 已平衡」狀態。
- 旅伴可新增與刪除；若旅伴已有付款、分攤或結算紀錄，會保守阻擋刪除以保留帳務完整性。
- 首頁月統計可切換「含旅行」與「日常」範圍；含旅行時只納入目前使用者選擇 include 的旅行分攤金額。
- 預算目前以月預算為主；已納入個人月報的旅行分攤會一起計入預算已花費。

尚未正式完成的範圍：

- 自動匯率 API。
- iOS 正式登入、Keychain session lifecycle、核心 CRUD 與 TestFlight；目前只有 read-only prototype。
- 旅行分類預算與進階旅行報表。

新的執行 Roadmap 見 `docs/product-roadmap.md`。舊 Phase 文件保留作為歷史紀錄，不再作為新工作的階段判定來源。

## 為什麼要調整方向

原本專案已經包含資產、預算、財務目標、報表與 LINE Bot 等功能，但功能範圍偏大，容易變成一般記帳 App 或全功能理財 App。

實際使用後發現，最需要解決的痛點是：

- 出國支出不想直接混進日常帳本
- 旅行途中想用當地幣別快速記錄
- 回來後想知道換算成本幣後實際花費
- 跟朋友出國時，想知道誰先付、誰該分攤、最後誰欠誰
- 想區分日常支出與旅行支出，但必要時又能合併分析
- 手機上要能很快完成記帳，不想操作複雜後台

因此接下來會將產品方向收斂為「日常 + 旅行 + 跨幣別 + 輕量分帳」。

## 核心使用情境

### 1. 日常記帳

平常記錄 TWD 收入與支出，例如餐費、交通、購物、娛樂等，並能查看本月支出、分類統計與簡單預算狀態。

### 2. 出國/旅行記帳

出國前建立一趟旅行，例如：

- 日本 2027
- 韓國自由行
- 歐洲出差

旅行期間可以用當地幣別記帳，例如 JPY、KRW、USD、EUR。每筆交易保留原始幣別與原始金額，同時可換算成主要幣別。

### 3. 旅行結算

旅行結束後產生結算：

- 旅行總支出
- 換算成本幣後的總金額
- 每日平均支出
- 分類支出占比
- 現金 / 信用卡 / 其他付款方式統計
- 旅伴分帳結果
- 誰欠誰多少
- 是否納入個人月報

### 4. 輕量分帳

旅行中可建立同行成員，並在每筆旅行支出中記錄：

- 誰付款
- 誰需要分攤
- 是否平均分攤
- 分攤後每個人應付多少

第一階段先完成「單人維護的分帳」並保留外部旅伴；Phase 5 開始加入多人帳本雛形，讓旅伴可透過邀請連結加入同一帳本。外部旅伴與真實登入使用者的自動合併仍暫緩，避免 MVP 流程過度複雜。

### 5. 手機快速輸入

手機是主要使用場景。Web 端會逐步調整成 App-like / PWA 體驗，並保留 LINE Bot 作為快速記帳入口。

## 目前已具備的功能

### 後端

- Flask REST API
- JWT 驗證
- LINE Login callback
- PostgreSQL 資料庫
- SQLAlchemy 資料存取
- 使用者資料隔離
- 資產帳戶管理
- 帳戶互轉與跨幣別轉帳
- 收入/支出交易管理
- 預算設定與超支檢查
- 財務目標管理
- 報表 API
- LINE Bot webhook
- Gemini 自然語言解析

### 前端

- Vue 3 + Vite
- LINE Login 登入頁
- 資產總覽
- 帳戶類型分組、收合與資金分配比例
- 交易紀錄
- 預算規劃
- 財務目標
- 儀表板圖表
- Vue Router 權限檢查
- Axios API client

### LINE Bot

- 自然語言記帳
- 查詢本月支出
- 查詢資產
- 新增收入/支出流程
- 新增帳戶流程
- 更新餘額流程
- 轉帳流程
- 設定預算流程

## 接下來的產品收斂

接下來會將功能分成三個層級。

### 主線功能

這些是優先強化的核心功能：

- 快速記帳
- 日常帳本
- 旅行帳本
- 多幣別交易
- 匯率換算
- 旅行成員
- 輕量分帳
- 旅行結算
- 手機優先 UI
- PWA 體驗
- LINE 快速輸入

### 支撐主流程的財務能力

這些能力用來支撐 Nomica 的個人財務管理主流程：

- 資產帳戶
- 基本預算
- 基本報表
- 手動 Asset Allocation（Web 已開放 Portfolio、Holding、投入成本、Snapshot 與新增投入試算）

資產帳戶可記錄現金、信用卡與不同付款方式，也能記錄薪資轉往儲蓄、旅費或投資帳戶的資金流向。Asset Allocation 後續只管理使用者自行輸入的 Portfolio、Holding、投入成本、目標比例與手動 Snapshot；不做券商串接、即時報價或完整交易績效。預算則維持月支出上限與旅行支出控制的職責。

### 暫緩或從主流程移除的功能

這些功能短期不再擴充，必要時會先從主導航或主要流程移除：

- 財務目標
- 行情導向的股票看盤與技術分析
- 自動投資建議與市場預測
- 完整理財規劃
- 多使用者 SaaS 化
- 多人即時共同編輯分帳
- 催款與付款通知
- AI 理財顧問

原因是這些方向容易讓產品變得過大，也會與現有成熟投資/資產管理 App 高度重疊。

## 開發 Roadmap

本專案以 Phase 作為主要開發階段。早期文件中的 Stage 已整併到下列 Phase，避免同時維護兩套進度表。

### Phase 1: 核心 MVP 與定位收斂

狀態：已完成。

目標：把產品收斂為「日常 + 旅行 + 跨幣別 + 輕量分帳」，並完成可本地測試的核心資料流。

已完成：

- 更新 README 與產品定位。
- 導入新版 PostgreSQL schema 與 Alembic。
- 建立旅行帳本、旅行成員、旅行交易、分帳、結算等核心資料模型。
- 日常交易與旅行交易可分開統計，也可由每位登入成員自行選擇是否把自己的旅行分攤納入首頁與收支統計。
- 旅行交易支援原始幣別、匯率與本幣換算。
- 旅行支出可指定付款人，且只有目前使用者付款時才可連動自己的帳戶。
- 支援平均分攤、自訂分攤、建議結算、確認結算與撤銷結算。
- 支援旅行封存、軟刪除、復原與永久刪除。
- Goals 暫時改為尚未開啟狀態。
- 補上核心 schema smoke test 與資料流文件。

### Phase 2: 手機優先體驗與 PWA 雛形

狀態：已完成第一輪收斂。

目標：讓 Web 端在手機上更像日常會打開的 App，優先處理入口、導航、表單與資訊密度。

預計任務：

- 重新整理手機版首頁資訊層級。
- 改善底部導航與主要操作入口。
- 建立快速新增交易入口。
- 讓日常記帳與旅行記帳的切換更直覺。
- 收斂旅行頁、收支頁、資產頁的 mobile layout。
- 補 PWA manifest 與基本安裝體驗。
- 評估是否加入基本離線殼層快取。

### Phase 3: 實際旅行前的操作打磨

狀態：核心完成，保留實際旅行前微調。

目標：在真實出國前，把旅行建立、記支出、分帳、結算流程調整到可以實戰使用。

已完成：

- 旅行支出表單再簡化。
- 匯率輸入與預設匯率體驗優化。
- 旅行總覽補上更清楚的支出、分帳與結算摘要。
- 旅行支出已更明顯區分「整團花費」、「我的分攤」與「待收 / 待付 / 已平衡」。
- 建議結算已調整為「誰付給誰多少」的方向式呈現。
- 旅行支出付款人若不是目前使用者，不會連動目前使用者的帳戶餘額。
- 已補資料流 smoke test，確認旅行支出、日常月報、近期紀錄、帳戶扣款與分帳摘要的關係。
- 旅伴支援刪除未使用成員；已被付款、分攤或結算引用的旅伴會被保護，不直接刪除。
- 分帳頁已提供文字版結算摘要複製，先支援手動貼給旅伴核對。
- 旅行交易支援編輯，更新金額、付款人、帳戶、匯率與分帳後會同步重算帳戶餘額與分帳摘要。
- 若旅行已有確認結算，編輯交易前會提示可能影響剩餘待收 / 待付金額。
- 分帳頁已加入旅行收尾檢查，提示支出筆數、待收待付與已確認付款狀態。
- 旅行交易可產生 CSV 內容，方便 Web 端備份、核對或用試算表檢視；直接下載體驗留待部署/瀏覽器環境驗證。

進行中：

- 實際旅行前用真實情境再檢查旅行支出表單是否足夠快、欄位是否還需要再收斂。

待評估：

- 直接下載 CSV / Excel 的跨瀏覽器體驗。
- 分享連結或圖片版結算摘要。
- 是否需要正式的旅行完成/鎖定流程。

Phase 3 到此先不再擴大旅行頁功能。後續若沒有實測發現阻塞，下一階段會轉向 Phase 4 的 LINE / AI 快速輸入整合，讓記帳入口更快，而不是繼續增加管理型功能。

### Phase 4: LINE / AI 快速輸入整合

狀態：核心完成。

目標：把原本 LINE Bot 語意記帳能力整理成可共用的後端解析服務，未來 Web / PWA / iOS 都能使用。

已完成：

- 建立 `AIParseService` 作為共用解析服務入口。
- LINE `MessageParser` 已改為包裝共用解析服務，保留既有 LINE legacy parse 格式。
- 建立 `AIParseEventManager`，LINE Bot 解析後會先寫入 `ai_parse_events`，作為後續 Web / PWA / iOS 共用解析紀錄的基礎。
- 建立 `POST /api/ai/parse` Web 快速輸入 API 雛形，目前只回傳解析結果並寫入 parse event，不直接建立交易。
- 收支頁已加入 AI 快速輸入欄初版，可先解析一句話並套用到既有表單，正式送出前仍由使用者確認。
- AI 解析結果套用後若成功新增交易，對應 `ai_parse_events` 會標記為 `confirmed` 並寫入交易 ID，方便後續追蹤解析採用率。
- LINE Bot 自然語言直接建立收入/支出時，也會把對應 parse event 標記為 `confirmed`，與 Web 快速輸入共用同一套採用追蹤語意。
- 建立 `GET /api/ai/parse-events` 查詢 API，可用於驗證最近解析紀錄與 confirmed 狀態。
- 收支頁在開發模式下顯示可收合的 AI 解析紀錄面板，用於檢查解析品質；正式使用與未來 App 主流程不一定顯示。
- 補上 parser 單元測試，避免 Phase 4 調整時破壞 LINE 既有解析契約。

後續維護項：

- Gemini API key / model 設定需在部署前重新確認。
- LINE Bot SDK 目前有 v3 deprecation warnings，後續可另開維護任務升級。
- AI 解析紀錄面板目前只作為 dev-only 觀察工具，不列入正式產品主流程。

### Phase 5: 實際旅行驗證與商品化評估

狀態：MVP 可用性初步通過，文件收尾完成，準備進入 Phase 5.5。

目標：用真實旅行資料與外部使用者回饋驗證產品定位，再決定是否商品化。

收尾結論：

- 核心功能可用性初步通過，日常記帳、帳戶、旅行帳本、分帳、多人邀請、LINE / AI 快速輸入皆已具備 MVP 測試基礎。
- 外部使用者初步回饋有正向訊號，AI 語意快速輸入具吸引力。
- 留存與使用頻率尚未完成驗證，移到 Phase 5.5 持續觀察。

驗證文件：

- `docs/phase5-validation-plan.md`
- `docs/phase5-simulation-test-script.md`
- `docs/multi-user-login-rollout-plan.md`
- `docs/deployment-checklist.md`
- `docs/phase5-5-roadmap.md`

驗證重點：

- 記帳流程是否夠快。
- 幣別切換是否自然。
- 匯率輸入是否麻煩。
- 分帳流程是否足夠簡單。
- 結算結果是否容易和朋友核對。
- 邀請連結、owner / editor / viewer 權限是否足夠支援約 10 人旅行共同記帳。
- LINE 與 PWA 哪個入口更順。
- 哪些功能應該保留、簡化或移除。
- 正式 LINE Login / 邀請連結 / 多人權限是否可在部署環境穩定運作。
- LINE Login 已改為後端發起並驗證 signed state，讓邀請連結登入導回流程更適合正式部署。

已知限制與延後項目：

- iOS 主畫面 PWA 的 LINE Login 目前不作為 Phase 5 解法，後續搭配同站網域、正式 session 或原生 App 再處理。
- 投資目前已有帳戶類型、資金流向與投入成本紀錄；Asset Allocation 已進入 schema / migration 地基，不接券商 API 或即時行情。
- 外部旅伴與登入旅伴自動合併暫緩，避免 MVP 階段誤合併。
- 自動匯率 API 暫緩，實際旅行前後再評估是否需要。

### Phase 5.5: 使用動機、操作效率與留存驗證

狀態：第一輪完成，進入後續觀察。

目標：在 Phase 5 MVP 可用性初步通過後，先提升日常打開理由、操作效率與使用者留存訊號，不急著擴大成完整投資或原生 App 模組。

優先方向：

- 帳戶活動追查與信用卡核對體驗。
- LINE / AI 快速記帳優化。
- 預算超支提醒。
- 首頁資訊可讀性與每日打開理由。
- 小幅 component 化與 UI 穩定。
- 使用者留存訊號蒐集。

目前已完成的 Phase 5.5 收斂：

- 首頁新增今日 / 本週摘要與輕量預算警示，讓使用者打開後能快速看到近期狀態。
- 帳戶頁支援單一帳戶近期活動追查，並可依全部 / 收入 / 支出 / 轉帳篩選；活動中的收支與轉帳可銜接既有編輯 / 刪除流程。
- 帳戶互轉已支援編輯與刪除，避免資金分配、儲蓄或投資投入成本記錯後只能手動補救。
- 收支頁 AI 快速輸入與 LINE help 已統一高頻輸入格式，並加入補記日期、帳戶提示與旅行帳本請回 Web 使用的說明。
- LINE 快速記帳已修正帳戶連動資料流；若有指定帳戶，Web 編輯該筆交易時仍會保留帳戶連結，避免重複扣款。
- 帳戶提示匹配已改為適用所有帳戶類型，避免只輸入「信用卡」或「銀行」時誤抓第一筆帳戶，並支援「國泰活存 / 國泰定存」這類同機構不同帳戶的較精準匹配。
- AI / LINE 分類已收斂為日常支出分類；投資投入成本改由帳戶互轉與投資類型帳戶記錄，不再作為一般支出分類。
- 支出分類已補上「工作」，用於公司代墊、工作相關費用等日常支出情境。
- LINE 回覆時間先以台灣時間顯示，完整使用者 / 旅行 timezone 模型列入後續重構。
- 旅行帳本建立後，每位登入成員可自行決定是否把自己的旅行分攤納入個人月報。

收尾結論：

- Phase 5.5 已完成留存與效率的第一輪收斂，包含首頁回訪理由、預算可見性、帳戶核對、LINE / AI 輸入一致性與近期高風險 bug 修正。
- Phase 6.1 到 Phase 6.7 第一版與最終回歸亦已完成，目前進入真實使用觀察與下一階段規劃；若後續測試發現阻塞級 bug，仍先以低風險修補處理。
- 此結論不代表市場驗證完成，使用頻率、留存與付費價值仍需後續真實使用資料驗證。

本階段不納入：

- 完整投資頁與券商串接。
- 原生 iOS App。
- 大型 UI 重設計。
- Google / Apple Login 完整商品化。

### Phase 6: 多人旅行、帳號與商品化基礎

狀態：第一版完成（2026-06-25），進入真實使用觀察與下一階段規劃。

目標：在 Phase 5.5 驗證日常使用與留存動機後，整理多人旅行與正式商品化前需要的基礎能力。

第一輪：Nomica Insights 首頁狀態中心。

- 首頁新增 `Nomica Insights`，回答「我現在需要注意什麼？」。
- V1 只使用系統已知事實，不做推測提醒、不新增 schema、不做信用卡到期日或用途分類。
- 目前提醒已收斂為三層：需要處理、值得注意、資訊；信用卡負數、預算超支與旅行月報偏好未決定會優先顯示。
- Money Flow 不取消，但移到 Phase 7，待資料模型與產品問題更成熟後再做。

Phase 6.1：TripMember 個人月報偏好與旅行分攤統計口徑。

- 同一旅行帳本是否納入月報改由每位登入成員自行決定。
- `pending` 與 `exclude` 不納入月報，只有 `include` 會納入。
- 多人旅行納入個人月報時，採用該使用者自己的分攤金額，不採用整筆旅行支出。
- 外部旅伴沒有個人月報偏好，不影響任何登入使用者的月報。

Phase 6.2 / 6.3：預算頁與首頁狀態中心收斂。

- 預算頁整理為本月預算控制狀態，包含總預算、已花費、剩餘、使用率、超支、快用完與未設定預算支出。
- 首頁 `Nomica Insights` 不承擔完整分析，只顯示跨模組需要注意的狀態與入口。

Phase 6.4：收支頁資訊架構與收入核對。

- 收支頁快速輸入已依收入 / 支出模式切換提示詞與範例，避免收入頁仍看到支出句型。
- 手動新增表單改為預設收合；AI 解析套用或手動新增時才展開，送出前仍由使用者確認日期、類別、帳戶與備註。
- 最近紀錄、支出分析與收入核對區文案已收斂，讓使用者更清楚每個區塊回答的問題。
- 收入模式新增「收入來源核對」，以總額卡、來源分布條與來源清單呈現本月收入來源，不新增 API 或複雜圖表。
- LINE 收入確認卡已修正中文 / 英文交易類型判斷，並在收入 / 支出成功卡補上類別顯示。

Phase 6.5：旅行頁狀態中心。

- 旅行頁新增「旅行狀態中心」，集中顯示個人月報偏好、分攤完整度、待收待付與類別比例狀態。
- 狀態卡可直接帶使用者前往交易、分帳或類別比例摘要，讓旅行頁更像可核對的操作中心。
- 本輪沿用既有旅行 overview、transaction splits 與 settlement suggestions，不新增 API 或 migration。
- 旅行支出表單只顯示支出類別，不再混入薪資、獎金、利息等收入類別。
- 記帳提醒通知先列為後續策略題，不在 Phase 6.5 直接實作推播或 LINE 主動提醒。

Phase 6.6：收支頁帳戶流向分析。

- 支出頁新增「付款來源分析」，依帳戶類型顯示現金、銀行、信用卡、電子錢包等付款來源金額與比例。
- 收入頁新增「入帳帳戶分析」，依帳戶類型顯示收入進到哪些帳戶。
- 多幣別依幣別分組，不在沒有正式匯率模型前硬加總。
- 未連動交易會列入「未連動帳戶」，協助使用者補足帳戶連動。
- 本輪由 `/api/transactions` 直接回傳 `account_type`，不新增 endpoint 或 migration。

Phase 6.7：資產頁帳戶健康度。

- 資產頁新增「帳戶健康度」，集中顯示信用卡負數、非信用卡負數、零餘額帳戶與未追蹤餘額帳戶。
- V1 只使用系統已知事實，不做信用卡繳款日、低水位門檻或推測型提醒。
- 本輪沿用既有 `/api/assets` 資料，不新增 API 或 migration。

Phase 6 收尾結論：

- Phase 6.1 到 Phase 6.7 第一版已完成，涵蓋個人旅行統計口徑、首頁狀態中心、預算控制狀態、收支資訊架構、旅行狀態中心、帳戶流向分析與帳戶健康度。
- 2026-06-25 最終回歸：前端 production build、ESLint、後端 pytest 與資料庫 schema smoke test 均通過。
- 首頁、收入 / 支出、預算、旅行與帳戶頁已完成桌面與 390px 手機寬度巡覽，未發現水平溢出或 JavaScript runtime error。
- 此處的「完成」代表 Phase 6 第一版功能與統計口徑可進入持續測試，不代表登入商品化、跨時區、正式匯率或原生 App 已完成。

Phase 7 前維護整理：

- 前端 routes 改為 lazy loading，各功能頁按需載入；原本約 559 KB 的單一 JavaScript bundle 已拆分，最大 chunk 約 189 KB。
- LINE Messaging API 已從 deprecated 相容介面遷移到 `line-bot-sdk` v3 的 webhook parser、Messaging API 與 request models。
- 現有 Flex Message JSON 與畫面維持不變，透過內部 adapter 轉成 v3 `FlexMessage`，避免重寫既有卡片。
- LINE v3 自動化測試、webhook signature 驗證與本地後端啟動均已通過；正式部署後仍需以官方帳號實測文字訊息、postback、reply 與 push。

Phase 7.1：Nomica 主帳號與正式 Session 地基。

- Nomica `users.id` 是主帳號；LINE、Apple、Google 都視為可綁定的 identity provider。
- Session 採 session-backed JWT：前端仍以 Bearer JWT 呼叫 API，但 JWT 必須綁定後端 `auth_sessions`，後端以 active session 作為有效性來源。
- LINE Login 保留為登入入口與快速記帳入口；LINE Bot 仍用同一個 Nomica user 寫入資料。
- 帳號設定頁先顯示目前 provider 狀態：LINE 已啟用，Apple / Google 尚未啟用。
- 本輪不做 refresh token、silent refresh、sliding session、cookie-only session、正式 Apple / Google OAuth 或裝置管理 UI。
- 後續規劃：Phase 7.2 優先接 Apple Login；Phase 7.3 再接 Google Login；帳號合併採登入後手動加綁，不使用 email 自動合併。

Phase App 0：iOS 原生殼 Prototype。

- 在 `ios/Nomica` 新增 SwiftUI iOS prototype，作為親手學習 iOS 開發與驗證 API 介面的起點。
- 第一版使用 SwiftUI、async/await、URLSession，不引入第三方套件。
- App 先讀取本地 dev API：`/api/auth/me`、`/api/dashboard/overview`、`/api/assets`、`/api/transactions`。
- iOS 端先提供首頁、收支、帳戶三個只讀 tab，不做新增、編輯、Apple Login、TestFlight 或 Push。
- 此階段不是正式 App 上架，也不需要 Apple Developer 付費帳號；正式 Apple Login 與 TestFlight 仍放後續階段。

Allocation 0：Asset Allocation Domain 定案。

- 已拆分 Account、Portfolio、Holding、Recorded Cost、Portfolio Snapshot 與 Bucket 的責任。
- Snapshot 是使用者在同一天建立的完整 Portfolio 快照，不是即時市值，也不自動改寫帳戶餘額。
- Allocation V1 只做投入成本、目標比例、手動 Snapshot 與新增資金配置試算；不提供賣出、選股、市場預測或交易建議。
- Bucket 屬於後續 Purpose Model，不納入 Allocation V1。
- 詳細規則見 `docs/asset-allocation-domain-plan.md`。

舊 Roadmap 的候選項目：

- 外部旅伴與真實登入使用者的安全合併流程，避免重複成員或誤合併。
- iOS 主畫面 PWA / 原生 App 登入策略，優先評估同站網域或原生 OAuth callback。
- Apple / Google Login 正式 OAuth 串接與 LINE 加綁流程。
- 完整 timezone 顯示模型，依使用者或旅行帳本時區顯示建立時間與交易時間。
- 自動匯率 API、旅行分類預算與進階旅行報表是否進入商品化版本。
- Phase App 1 的正式 session 儲存、Keychain 與核心 CRUD；手動 Snapshot 仍不接券商或即時行情。

新 Roadmap 執行順序：

1. M0：Finance Contract、Balance Contract、Settlement Ownership 與 Product Event Taxonomy。
2. M1：Mobile UX、Trip route 拆分、Universal Add、Home 與 Analysis 收斂。
3. M2：PWA Alpha 操作驗證。
4. M3：Balance Anchor、Adjustment、Settlement Account Entry 與 Reconciliation。
5. M4 至 M5：Travel Product 與 PWA Beta。
6. M6：iOS Auth Foundation、Vertical Slice 與 TestFlight。
7. M7 至 M9：依 Beta 數據決定 LINE Travel Context、App Store 與 Plus。

完整範圍、驗收條件與暫緩項目見 `docs/product-roadmap.md`。Money Flow、Allocation 擴充與 Bucket 不再是目前緊接的開發項目。

## 進度 Check

| 項目 | 狀態 | 備註 |
| --- | --- | --- |
| 產品定位收斂 | 完成 | 對外定位為整合記帳、帳戶、旅行與資產配置的個人財務工具；Personal Finance OS 作為長期內部願景 |
| README 與方向文件 | 完成 | 已補目前進度、核心資料流與測試方式 |
| M0 Finance Contract | 第一版完成 | 已固定 Payment、Expense、Settlement、Transfer、Adjustment、Balance 與 ownership 語意，建立安全的 Product Event Taxonomy；後端 102 tests 與前端 build 通過 |
| 新版 schema / Alembic | 完成 | 本地 migration 與 smoke test 可跑 |
| Asset Allocation 1A | 完成 | 已建立 Portfolio、Holding、Recorded Cost 與 Snapshot schema / migration |
| Asset Allocation 1B | 完成 | 已建立共用 Manager / API、ownership 與幣別驗證、轉帳成本分配、完整 Snapshot 與新增投入試算 |
| Asset Allocation 1C | 完成 | Web 已提供獨立資產配置列表、配置標的、投入成本、手動 Snapshot 與新增投入試算；帳戶頁提供入口 |
| 日常收支 | 完成 | 支援收入、支出、帳戶餘額連動、交易編輯、近期日期篩選、AI 快速輸入分流、收入來源核對、帳戶流向分析與支出分析文案收斂 |
| 帳戶與資金流向 | 完成第一輪 | 支援帳戶類型分組、信用卡負數、帳戶健康度、同/跨幣別帳戶互轉、investment 投入成本紀錄與單一帳戶近期活動追查 |
| 旅行帳本 | 完成 | 支援建立、切換、封存、軟刪除、復原、永久刪除，並支援每位登入成員自行決定是否納入個人月報 |
| 多幣別旅行交易 | 完成 | 支援原幣別、匯率、本幣換算 |
| 分帳 MVP | 完成 | 支援平均分攤、自訂分攤、建議結算 |
| 結算確認 | 完成 | 可確認 / 撤銷，不連動帳戶餘額 |
| 日常統計含旅行切換 | 完成 | 首頁與收支統計支援含旅行 / 日常範圍切換；旅行納入時採個人分攤金額 |
| 預算邏輯收斂 | 完成 | 預算已花費跟隨個人月報口徑，只納入使用者選擇 include 的旅行分攤 |
| 手機優先 UI | 完成第一輪 | 已整理底部導航、首頁、收支、旅行、帳戶、預算入口、收支列表 10 筆預覽、旅行支出預設自己負擔與首頁比例說明 |
| PWA / Nomica 品牌 | 完成基礎 | 已補 Nomica manifest、app icon、apple-touch-icon、favicon 與 production service worker 基礎 |
| 旅行前操作打磨 | 核心完成 | 已完成表單簡化、匯率/帳戶提示、分帳摘要、結算方向呈現、資料流一致性 smoke test、文字版結算摘要複製、旅行交易編輯與 CSV 內容產生 |
| LINE / AI 共用解析服務 | 核心完成 | 已建立共用解析服務入口、parse event 紀錄、Web parse API、查詢 API、收支頁快速輸入欄與 dev-only 解析紀錄面板；LINE 收入確認卡與類別顯示已修正 |
| Phase 5 MVP 模擬測試 | 完成 | 已補 10 人旅行假資料測試，並修正交易/分帳失敗時的 atomic rollback 問題；外部使用者初步測試回饋已納入 Phase 5 收尾 |
| 多人共同編輯 | 第一版完成 | 已補邀請連結、加入/重新加入、member 上限、owner/editor/viewer 權限、共享旅行交易查詢、帳戶資訊隔離與 dev 測試使用者切換 |
| Phase 5.5 留存與效率驗證 | 第一輪完成 | 已補今日/本週摘要、預算警示、帳戶活動篩選、帳戶互轉編輯刪除、AI/LINE 輸入引導、帳戶匹配修正與小幅 component 化；後續進入觀察 |
| Phase 6 多人旅行與商品化基礎 | 第一版完成 | Phase 6.1 到 6.7 與最終回歸已完成；Money Flow 移到 Phase 7，帳號 provider、iOS/PWA 登入、timezone、匯率與投資/資金分配獨立頁列入後續評估 |
| 自動匯率 API | 暫緩 | 實際旅行前再評估 |

## 核心資料流

### 日常收支

1. 使用者在 Web / LINE / 未來 App 建立一筆日常收入或支出。
2. 交易寫入 `transactions`，`trip_id` 為空。
3. 若有選擇自己的帳戶，且帳戶有追蹤餘額，支出會扣帳戶餘額，收入會加回帳戶餘額。
4. 日常交易會進入日常月報、日常近期紀錄與日常預算計算。

### 旅行支出

1. 使用者先建立 `trips`，系統會自動建立 owner 對應的 `trip_members`。
2. 新增旅行支出時，交易寫入 `transactions`，並帶入 `trip_id`、`paid_by_member_id`、原幣別、匯率與換算後本幣金額。
3. 若付款人是目前登入使用者，才允許連動自己的帳戶餘額。
4. 若付款人是外部旅伴或未來其他使用者，MVP 不連動目前使用者的帳戶。
5. 分攤結果寫入 `transaction_splits`，用於計算每位旅伴的已付款、應分攤與淨額。
6. 若目前登入成員的 `monthly_report_preference` 為 `include`，該成員自己的分攤金額會出現在首頁與收支統計的「含旅行」範圍。
7. `pending` 與 `exclude` 不納入個人月報；外部旅伴不適用個人月報偏好。

### 多人旅行帳本

1. owner 可建立一組有效 30 天的邀請連結；同一趟旅行同時間只保留一組 active invite。
2. 邀請連結可重複使用，active member 上限先固定為 15 人。
3. 受邀使用者登入後接受邀請，會建立自己的 `trip_members` 紀錄；若曾退出，會重新啟用原 member。
4. owner 可關閉邀請連結，也可調整非 owner 成員的 `editor` / `viewer` 權限。
5. editor 可新增旅行交易，但只能編輯或刪除自己建立的交易。
6. 若 editor 後續被降為 viewer，便不可再編輯或刪除自己過去建立的交易。
7. owner 可編輯或刪除同帳本內所有旅行交易，並且只有 owner 可封存、刪除或復原旅行帳本。
8. viewer 只能閱讀；前端也會隱藏新增支出入口，避免誤以為可以操作。
9. 分帳還款確認只允許 owner 或付款方本人操作；撤銷結算只允許 owner 或該筆結算記錄者操作。
10. 個人帳戶資訊仍以使用者隔離；共享旅行交易可見，但不會洩漏其他使用者的帳戶名稱或餘額。
11. owner 手動新增的外部旅伴與真實登入使用者自動合併仍暫緩，後續再設計避免誤合併。
12. 同一旅行帳本是否納入月報以 `trip_members.monthly_report_preference` 為準；`include` 才納入，`pending` / `exclude` 不納入。
13. 多人旅行進個人月報時，只採用該使用者自己的 `transaction_splits.converted_share_amount`，不採用整筆旅行交易金額。

### 多人功能本地測試

在 `DEV_AUTH_BYPASS=true` 與 `VITE_DEV_AUTH_BYPASS=true` 的本地開發環境中，前端右上角會顯示 dev-only 的測試使用者切換器，可切換 `Dev User`、`Amy`、`Ben`、`Cara`。

此切換器只用於本地測試多人邀請與權限流程：

- 一般視窗可用 `Dev User` 建立旅行與邀請連結。
- 無痕視窗可切成 `Amy` 接受邀請，模擬另一位使用者加入。
- owner 可將 Amy 在 `editor` / `viewer` 間切換，驗證新增、編輯、刪除與分帳結算權限。
- 此機制透過 `X-Dev-User` header 傳給後端，且後端只在非 production 的 `DEV_AUTH_BYPASS=true` 下接受。

### 分帳與結算

1. 分帳摘要由 `transactions`、`transaction_splits` 與 `settlements` 即時計算。
2. 建議結算會依每位旅伴的淨額產生「誰付給誰多少」。
3. 標記已付款會新增 `settlements` 紀錄。
4. 撤銷已付款會軟刪除該 `settlements` 紀錄。
5. 結算紀錄只調整分帳淨額與建議結算，不會異動任何帳戶餘額。

### 封存與軟刪除

1. 封存旅行會將 `trips.status` 改為 `archived`，資料仍保留，可解除封存。
2. 刪除旅行與交易目前採軟刪除，會立即從一般查詢隱藏並寫入 `deleted_at` 與 `purge_after`。
3. 軟刪除帳本可在旅行管理區復原。
4. 刪除暫存區可執行永久刪除；此操作不可復原，正式產品流程仍建議保留二次確認。
5. `purge_after` 代表刪除 30 天後符合永久清理資格；目前尚未確認有定期自動 purge worker，因此不可解讀為系統一定會在第 30 天自動清除。
6. 未刪除的收入、支出、旅行與帳戶關聯資料會保留至使用者主動刪除；資料匯出、帳號刪除與正式 retention policy 排在 M8 Release Engineering。

## 技術棧

### Backend

- Python
- Flask
- Flask-CORS
- SQLAlchemy
- PostgreSQL
- PyJWT
- python-dotenv
- LINE Bot SDK
- Google Gemini API
- gunicorn

### Frontend

- Vue 3
- Vite
- Vue Router
- Axios
- Chart.js
- vue-chartjs
- SweetAlert2
- date-fns

### Deployment

- Backend: Render
- Frontend: Vercel
- Database: Supabase PostgreSQL

目前部署使用免費額度，因此可能會遇到冷啟動問題。短期可透過 healthcheck 定時喚醒改善；若未來需要穩定使用，可評估付費 instance 或改用其他部署方案。

## 專案架構

```text
.
├── web_app.py                 # Flask API 與 LINE callback / webhook 入口
├── config.py                  # 共用設定
├── models/
│   ├── schema.py              # SQLAlchemy table schema
│   ├── database.py            # DB engine / session
│   ├── asset_manager.py       # 資產帳戶管理
│   ├── budget_manager.py      # 交易與預算管理
│   ├── goal_manager.py        # 財務目標管理
│   ├── user_manager.py        # 使用者管理
│   └── linebot/               # LINE Bot parsing / flows / responses
├── reports/                   # 報表格式化邏輯
├── scripts/                   # 手動測試與 LINE rich menu 工具
├── data/                      # 早期 JSON 資料，現階段主要資料來源已改為 DB
└── frontend/
    ├── src/
    │   ├── views/             # Vue pages
    │   ├── components/        # Vue components
    │   ├── router/            # Vue Router
    │   └── api.js             # Axios client
    ├── vite.config.js
    └── vercel.json
```

## 本地開發

### Local Database

本地開發建議使用 Docker / OrbStack 啟動獨立 PostgreSQL，避免直接操作 Supabase production。

```bash
docker compose up -d postgres
```

本地資料庫連線：

```env
DATABASE_URL=postgresql://personal_finance:personal_finance@localhost:5433/personal_finance
```

目前 production DB 在 Supabase PostgreSQL。接下來旅行、多幣別與分帳功能會先在本地 DB 驗證 schema，再決定如何重建或遷移 production。

本地套用新版 schema：

```bash
alembic upgrade head
```

本地 schema smoke test：

```bash
docker exec personal_finance_postgres createdb -U personal_finance personal_finance_test
RUN_DB_SMOKE_TESTS=1 TEST_DATABASE_URL=postgresql://personal_finance:personal_finance@localhost:5433/personal_finance_test pytest -q tests/test_schema_smoke.py
```

Smoke test 會重建測試資料庫內的 schema，因此必須使用 `TEST_DATABASE_URL`，且資料庫名稱需以 `_test` 結尾。不要把 `TEST_DATABASE_URL` 指向本地開發 DB 或 Supabase production。

目前 smoke test 覆蓋的關鍵資料流：

- 建立使用者與登入身份。
- 建立帳戶與幣別。
- 建立旅行與 owner member。
- 新增外部旅伴。
- 旅行封存、解除封存、軟刪除、復原與永久刪除。
- 新增旅行支出，並驗證只有自己付款時才可連動自己的帳戶。
- 平均分攤與自訂分攤。
- 日常支出、收入與刪除收入後的帳戶餘額回復。
- 預算已花費會依個人月報口徑計算。
- 首頁與收支統計可包含「納入個人月報」的旅行分攤金額。
- 建議結算、確認結算與撤銷結算。
- 結算紀錄不異動帳戶餘額。

一般測試與前端 build：

```bash
pytest -q

cd frontend
npm run build
```

### Backend

建議使用 Python 3.12。Python 3.14 目前可能讓部分套件缺少 wheel，導致 `psycopg2-binary`、`grpcio` 等套件需要從原始碼編譯。

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python web_app.py
```

後端需要設定環境變數，例如：

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `LINE_LOGIN_CHANNEL_ID`
- `LINE_LOGIN_CHANNEL_SECRET`
- `LINE_MSG_CHANNEL_ACCESS_TOKEN`
- `LINE_MSG_CHANNEL_SECRET`
- `GEMINI_API_KEY`
- `VITE_BACKEND_BASE_URL`
- `FRONTEND_BASE_URL`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Production build / PWA 預覽：

```bash
cd frontend
npm run build
npm run preview
```

Service Worker 只會在 production build 註冊；本地 `npm run dev` 不會啟用快取，避免開發測試時被舊資源影響。

前端需要設定：

- `VITE_APP_API_URL`
- `VITE_LINE_LOGIN_CHANNEL_ID`

## 商品化方向

短期目標不是立即商品化，而是先做成自己真的會使用的工具。

若未來要商品化，可以考慮聚焦在：

- 常出國的人
- 留學生
- 數位遊牧者
- 跨國工作者
- 自由工作者
- 需要同時處理日常、旅行支出與朋友分帳的人

可能的付費功能：

- 多旅行帳本
- 自動匯率更新
- 旅行結算進階報表
- 分帳結果分享連結
- 進階分帳規則
- CSV / Excel 匯出
- 雲端同步
- PWA / iOS App 體驗

## 現階段原則

- 優先解決自己真實會遇到的問題
- 不追求全功能理財平台
- 不與成熟投資管理 App 正面競爭
- 先讓日常與出國記帳變得順手
- 分帳先解決旅行中的常見情境，不做完整多人協作平台
- 實際使用後再決定功能是否保留、簡化或移除
