# Asset Allocation Domain Plan

## 狀態

- 階段：Allocation 0
- 目的：在建立 migration、API 與 UI 前，先固定產品邊界與資料語意。
- 適用端：Web、LINE 與 iOS 共用後端資料模型；不是 iOS 專屬功能。

## 產品定位

Nomica 的長期內部願景是 Personal Finance OS，協助使用者管理自己的收支、帳戶、旅行與資產配置。

對外說明維持具體：

> Nomica 是整合記帳、帳戶、旅行與資產配置的個人財務工具，協助使用者掌握資金位置與自己制定的配置策略；不提供行情、選股、交易或買賣建議。

Asset Allocation 的邊界是管理使用者自己輸入的策略與資料，不管理市場：

- 不串接券商。
- 不提供即時行情、K 線、新聞或技術分析。
- 不選股、不預測報酬、不自動下單。
- 不產生賣出建議。
- 可依使用者自己設定的目標比例，提供新增資金的配置試算。

## Domain 邊界

### Account

回答「錢放在哪裡」。

例如銀行、現金、信用卡或投資帳戶。現有 `accounts.balance` 維持帳戶層級的記錄餘額，帳戶互轉仍只改變來源與目標帳戶餘額。

### Portfolio

回答「這一組資產採用什麼配置策略」。

Portfolio 保存名稱與基準幣別，並包含多個 Holding。V1 可跨多個投資類型 Account，但同一個 Portfolio 只使用一種基準幣別；所連結 Account 的幣別也必須相同。

### Holding

回答「實際配置在哪個標的」。

例如 0050、00631L、VOO、債券或 BTC。Allocation V1 的 Holding 必須連結所屬的投資類型 Account，並保存使用者設定的目標比例；它不是銀行帳戶，也不直接取代 Account。

### Recorded Cost

回答「使用者記錄投入了多少」。

成本採可追溯的 Cost Entry 累加，不把累積成本當成可任意覆蓋的單一市值欄位。Cost Entry 可選擇連結既有帳戶互轉，也允許使用者建立手動調整，以承接上線前的歷史投入。

這裡的 Recorded Cost 是 Nomica 的投入紀錄，不宣稱等同券商稅務成本或完整交易 lot 成本。

### Portfolio Snapshot

回答「在某一天，整個 Portfolio 的手動記錄價值是多少」。

Snapshot 必須屬於 Portfolio，並在同一日期包含所有 active Holding 的價值。這可避免不同 Holding 使用不同日期，卻被錯誤組成同一份目前配置。

Snapshot 是使用者手動輸入的時間點資料，不是即時市值。V1 不用 Snapshot 自動改寫 `accounts.balance`，也不把 Account balance 與 Snapshot value 相加。

### Bucket

回答「這筆資金準備拿來做什麼」。

例如緊急金、DCA、加碼池、旅遊或買房。Bucket 屬於 Purpose Model，會涉及一個帳戶拆成多個用途、同一用途橫跨多個帳戶，以及分配總額不可超過可用餘額等規則。

Bucket 不納入 Allocation V1，等 Portfolio 與 Snapshot 使用方式穩定後再進入 Allocation 2。

## V1 資料語意

```text
Account.balance
= 帳戶層級記錄餘額

Holding recorded cost
= Cost Entries 合計

Snapshot value
= 某一天由使用者手動輸入的資產價值
```

三者不可混用：

- Asset Allocation V1 不將 Snapshot value 再加進既有帳戶總資產，避免重複計算。
- 帳戶互轉到投資帳戶，不會自動猜測應分配到哪個 Holding。
- 使用者可把 Cost Entry 連結到 transfer，明確指定投入的 Holding。
- 同一筆 transfer 可在未來支援分配至多個 Holding，但所有關聯 Cost Entry 合計不得超過該筆 transfer 的目標金額。
- 手動 Cost Entry 必須標示為 manual，避免被誤認為由帳戶互轉產生。

## Allocation V1 範圍

### 支援

- 建立與編輯 Portfolio。
- 建立、編輯與停用 Holding。
- 設定 Holding 目標比例。
- 新增、編輯與刪除 Recorded Cost Entry。
- 建立完整的 Portfolio Snapshot。
- 比較目標比例與最近一次完整 Snapshot 的目前比例。
- 沒有 Snapshot 時，可顯示「依投入成本」的配置，但不得稱為目前配置。
- 輸入新增資金後，依使用者目標比例產生配置試算。

### 不支援

- 券商 API、即時行情與自動更新價格。
- 股數、成交價、交易 lot、股息、稅務成本或已實現損益。
- 自動匯率與跨幣別 Portfolio 換算。
- 賣出、停損、選股或預測型建議。
- Bucket / Purpose Model。
- AI 投資建議。

## 建議資料模型

正式 migration 前預計拆成：

```text
portfolios
├─ id
├─ user_id
├─ name
├─ base_currency
├─ is_active
└─ timestamps

holdings
├─ id
├─ portfolio_id
├─ account_id (required, V1 僅允許 investment account)
├─ name
├─ symbol (nullable)
├─ asset_class (nullable)
├─ target_weight
├─ is_active
└─ timestamps

holding_cost_entries
├─ id
├─ holding_id
├─ source_transfer_id (nullable)
├─ entry_type (transfer | manual_adjustment)
├─ amount
├─ currency
├─ occurred_on
├─ note
└─ timestamps

portfolio_snapshots
├─ id
├─ portfolio_id
├─ snapshot_date
├─ currency
├─ note
└─ timestamps

portfolio_snapshot_items
├─ id
├─ snapshot_id
├─ holding_id
└─ value
```

資料表名稱與欄位會在 migration 實作前再次依現有 schema 命名慣例核對；本文件先固定責任與資料關係。

## 驗證規則

- 建立與編輯 Holding 時允許目標比例尚未完成；執行目標配置比較或 allocation preview 前，active Holding 的目標比例合計必須為 100%。
- 比例保存為 decimal，不用浮點數直接比較。
- Cost Entry 與 Portfolio 必須使用相同基準幣別；V1 不隱性換匯。
- Holding 若連結投資 Account，Account 的 user、type 與 currency 必須符合 Portfolio；Cost Entry 連結的 transfer 也必須轉入該 Holding 所屬 Account。
- Snapshot 必須包含當下所有 active Holding，且每個 Holding 只能出現一次。
- Snapshot value 不得為負數。
- 同一 Portfolio 同一天只保留一份 active Snapshot；修改採更新既有 Snapshot。
- 已連結 transfer 的 Cost Entry 合計不可超過 transfer 的 target amount。
- 刪除 Holding 前若已有 Cost Entry 或 Snapshot，應改為停用，不直接硬刪除歷史。

## Allocation 1A Schema 決議

- V1 只管理 investment Account 中的投資資產，不把銀行、現金或信用卡重複建成 Holding。
- Portfolio 採單一基準幣別；不同幣別建立不同 Portfolio，不在 V1 引入手動或自動匯率。
- Holding 必須連結 Account；同一 Portfolio 可跨多個同幣別的 investment Account。
- 目標比例允許先以草稿保存，配置比較與新增投入試算時才要求 active Holding 合計為 100%。
- 一筆 transfer 可分配至多個 Holding；帳戶 ownership、type、currency 與分配總額由 Allocation 1B service 在同一 transaction 驗證。

## 新增資金配置試算

試算只使用使用者自己設定的目標比例，不使用 AI 或市場預測。

若存在完整 Snapshot：

```text
預計投入後總額 = 最近 Snapshot 總額 + 新增資金
各 Holding 目標金額 = 預計投入後總額 × 目標比例
配置缺口 = max(0, 目標金額 - 最近 Snapshot value)
```

新增資金依各 Holding 的正向配置缺口比例分配；結果只稱為「新增投入試算」，不稱為買賣建議。

若沒有完整 Snapshot，可用 Recorded Cost 進行試算，但畫面必須標示「依投入成本試算」，不得與 Snapshot 配置混為同一口徑。

## API 草案

```text
GET    /api/portfolios
POST   /api/portfolios
GET    /api/portfolios/<portfolio_id>
PATCH  /api/portfolios/<portfolio_id>

POST   /api/portfolios/<portfolio_id>/holdings
PATCH  /api/holdings/<holding_id>
POST   /api/holdings/<holding_id>/cost-entries

POST   /api/portfolios/<portfolio_id>/snapshots
GET    /api/portfolios/<portfolio_id>/snapshots

POST   /api/portfolios/<portfolio_id>/allocation-preview
```

所有 API 沿用 Nomica user 與 session 驗證，不建立 iOS 專用 endpoint。LINE V1 不提供 Portfolio 編輯，只保留 Web / iOS 操作入口。

## 開發順序

### Phase App 0

- 完成 iOS 首頁、收支、帳戶只讀與錯誤狀態驗收。

### Allocation 0

- 完成本文件、README 與 roadmap 定位同步。
- 不新增 migration 或 UI。

### Allocation 1A

- 建立 schema、migration、constraints 與 DB smoke tests。

### Allocation 1B / 1C

- 1B 建立 manager/service、API、ownership validation 與後端測試。
- 1C 由 Web 驗證 Portfolio、Holding、Cost Entry、Snapshot 與配置試算。
- Snapshot 暫不影響既有資產總額。

### Phase App 1 / 1.5

- App 1 處理正式 session 儲存與核心 CRUD。
- App 1.5 再接入已穩定的 Asset Allocation API。

### Allocation 2

- 規劃 Bucket / Purpose Model。

### Allocation 3

- AI 只負責解釋使用者設定與確定性試算結果，不提供市場預測或投資建議。

## Allocation 0 完成條件

- Account、Portfolio、Holding、Recorded Cost、Snapshot、Bucket 的責任沒有重疊。
- Snapshot 與既有 Account balance 不會重複計入資產總額。
- V1 的多幣別、成本、配置比例與停用規則已寫清楚。
- 新增資金試算不包含賣出或市場預測。
- Web 與 iOS 共用同一組 API 與資料模型。
