# Nomica API Contract Baseline

本文件記錄 2026-10-07 Web／PWA 已使用、未來 iOS client 可依賴的第一版 API contract。它是既有行為的 characterization，不代表已完成公開 API versioning。

## 共通規則

- 需要登入的 endpoint 使用 session-backed JWT。Web 使用同源 proxy 與 HttpOnly Cookie；callback 不傳 URL Token，前端不再保存／自動傳送 localStorage Bearer。明確的非瀏覽器 Bearer client 仍受後端 Session 驗證。部署要求見 `security-boundary-hardening.md`（migration `20261021_0018`）。
- UUID 以 JSON string 傳輸。
- 日期使用 `YYYY-MM-DD`；時間使用含 timezone 的 ISO 8601 string。
- 金額、匯率與換算金額目前使用 JSON number。Client 不應自行用 binary floating point 重新計算帳務結果。
- nullable 欄位保留為 JSON `null`，不以空字串代替。
- 一般成功 response 使用 `{ "success": true, "data": ... }`；寫入操作可另外包含 `message`、`replayed`。
- 一般錯誤使用 `{ "success": false, "message": "..." }`。Auth middleware 的 401 response 目前是 legacy `{ "message": "..." }`，client 應以 HTTP status 判斷 session 失效，不依賴單一錯誤文案。
- 帳務、旅行、配置、解析與分析 API 的未預期 DB／內部錯誤回 500，訊息不包含 SQL、參數或 provider 細節；已知業務驗證仍依各 endpoint 回 400／404，冪等資料衝突回 409。舊版部分入口曾把 DB 失敗回 400／404，client 不應沿用此假設。
- 寫入收到 5xx 或斷線時不得直接推定未提交；有 `client_request_id` 契約的操作應保留原 key 與 payload，依原請求重試。其餘操作先核對紀錄，不能自行更換意圖重送。
- 收到 401 時，Web／iOS 必須清除失效憑證並回到登入流程；不得持續重送同一 token。

## Auth

### `GET /api/capabilities`

需登入，回傳 `{success:true,data:{ai_parse:boolean,line_interactions:boolean}}`，
不快取。未完成公開驗收時預設兩者為 false；Web `/api/ai/parse` 回 503
`code=AI_DISABLED`，不解析／不保存新事件。LINE 暫停互動但不影響 LINE Login。
本機 synthetic 模式及 G-AI 邊界見 `security-boundary-hardening.md`。

### `GET /api/auth/me`

成功的 `data`：

```json
{
  "user_id": "uuid",
  "name": "Display Name",
  "provider": "line",
  "session_id": "uuid",
  "is_admin": false
}
```

`is_admin` 只有在該使用者的 LINE 身分等於 `NOMICA_ADMIN_LINE_USER_ID` 時為 `true`，供「我的」頁決定是否顯示「使用概況」。`provider` 與 `session_id` 在正式 session response 中存在。Dev auth bypass 只保證 `user_id` 與 `name`，不得作為正式 client contract。

### `GET /api/admin/usage`

只有營運者（LINE 身分等於 `NOMICA_ADMIN_LINE_USER_ID`）可用；其他人一律回 404，與不存在的路由相同。`data` 為 `total_users`、`active_users`（近 `recent_days` 天有記帳）、`recent_days` 與 `users`（最多 200 位，依最後記帳時間排序）。每位使用者只有 `name`、`joined_at`、`last_record_at`、`total_records`、`recent_records`，不含金額、品項、備註或任何帳務內容。

## Accounts

### `GET /api/assets`

`data` 是以 account ID 為 key 的 object，不是 array。每個 account 至少包含 `id`、`account_key`、`bank_name`、`account_type`、`currency`、`balance` 與 `credit_card_billing`。

信用卡帳期資料可能為 `null`；存在時格式為：

```json
{
  "closing_day": 5,
  "due_day": 20,
  "due_month_offset": 1,
  "override_closing_date": null,
  "override_due_date": null,
  "next_closing_date": "2027-03-05",
  "next_due_closing_date": "2027-03-05",
  "next_due_date": "2027-03-20",
  "next_due_date_source": "estimated",
  "today": "2027-02-10"
}
```

`today` 是後端依使用者 timezone 計算排程時採用的日期；`next_due_date_source` 目前為 `estimated` 或 `user_set`。帳期資料不代表本期應繳金額、繳款狀態或逾期判定。

### `POST /api/assets`

公開新增帳戶必須傳 `client_request_id` UUID，並帶上 `bank_name`、`account_type`、`balance`。缺少有效 key 回 400，無帳務寫入。

- 首次成功回 201。相同使用者、key 與原始資料重送回 200，並帶原始 `data.account_id` 和 `replayed: true`。`data.transaction_id` 為 `null`。
- 相同 key 改用於不同資料回 409 `REQUEST_PAYLOAD_CONFLICT`。已提交資料包含開戶餘額、幣別、樣式及信用卡帳期設定。回放只回傳原結果，保留之後的編輯或刪除。
- Web 送出前先保存原始資料與 key。結果不明時只以原資料重試。Web 同時傳原使用者的 `X-Nomica-Request-Owner`，若與實際登入者不同，回 409 `REQUEST_OWNER_CHANGED`。
- 部署前同步更新所有新增帳戶的 client，缺 key 的舊版會收到 400。此變更沿用既有 `financial_commands` schema。

### `PUT /api/assets/:accountId`

可編輯帳戶名稱、類型、樣式和信用卡帳期。傳入既有幣別可正常編輯，變更幣別回 400。
若含 `balance` 或 `new_balance`（包含零或 `null`），整筆回 400，基本資料與帳務均不寫入。
舊 client 須將餘額校正改走下列 POST 並傳入 `client_request_id`。

### `POST /api/assets/:accountId/adjustments`

公開餘額校正必須傳 `client_request_id` UUID、`new_balance`（目標餘額）及 `reason`，可選 `note`。缺少有效 key 或無法儲存的金額／差額回 400，無帳務寫入。

- 首次成功回 201。相同使用者、key、帳戶、原目標餘額、原因及備註回 200，並帶原校正 ID 和 `replayed: true`。重試只回傳原結果，保留此後的餘額異動。
- 同 key 不同資料回 409 `REQUEST_PAYLOAD_CONFLICT`。舊 key 僅在不可編輯的校正紀錄能核對相同原目標餘額、原因、備註及帳戶時回放。
- Web 依登入者及帳戶保存待確認校正，重整或結果不明時可用原資料重試。`X-Nomica-Request-Owner` 與實際登入者不同回 409 `REQUEST_OWNER_CHANGED`。
- 校正更新帳戶快照並記錄 Adjustment，不列入收入或支出。部署前同步更新所有寫入 client，缺 key 的舊版會收到 400。此變更沿用既有 schema。

### `GET /api/assets/:accountId/activity`

使用 page pagination：

```json
{
  "success": true,
  "data": {
    "items": [],
    "pagination": {
      "page": 1,
      "limit": 20,
      "has_next": false,
      "has_prev": false,
      "filter": "all"
    }
  }
}
```

`filter` 支援 `all`、`income`、`expense`、`transfer`、`settlement`、`adjustment`。目前此 endpoint 不提供 `total_count`。

## Transactions

### `GET /api/transactions`

沒有任何分頁或篩選 query 時，為相容既有 client，`data` 仍直接是 transaction array。

只要帶入 `trip_id`、`type`、`month`、`date`、`limit` 或 `cursor`，response 使用 cursor pagination：

```json
{
  "success": true,
  "data": [],
  "pagination": {
    "next_cursor": null,
    "has_more": false,
    "limit": 20,
    "total_count": 0
  }
}
```

- `limit` 必須介於 1 至 50；旅行交易省略時預設 20。
- `month` 使用 `YYYY-MM`，`date` 使用 `YYYY-MM-DD`。
- Cursor 是 opaque token，client 不得解析或自行產生。
- 變更主要篩選條件、完成新增／編輯／刪除後，client 應回到第一頁。

旅行交易 response 另外包含 `trip_transaction_summary`，其統計不受目前頁面的 20 筆限制：

```json
{
  "total_count": 0,
  "expense_count": 0,
  "missing_split_count": 0,
  "date_counts": [],
  "category_totals": []
}
```

## Trip overview

### `GET /api/trips/:tripId/overview`

成功 response 的 `data` 固定包含：

- `trip`
- `transactions`
- `transaction_pagination`
- `transaction_summary`
- `split_summary`
- `settlement_suggestions`
- `settlements`
- `invite`

`transactions` 僅為第一頁 20 筆；狀態卡、日期、缺少分攤數及類別統計必須使用 `transaction_summary`，不可從目前頁面重新推算。

## 相容性原則

### 財務建立命令（2026-10-20）

`POST /api/transfer`與`POST /api/trips/:tripId/settlements`新增必填UUID `client_request_id`。缺key／格式不合法400，同使用者同operation同key但不同payload409。相同payload重送回原ID與`replayed=true`；Transfer維持200，群組結算初次201／重播200。成功`data`分別包含`transfer_id`／`settlement_id`。

此為必填欄位的獨立相容性遷移批次；需先部署migration `20261020_0017`並同步更新寫入client。Web未知提交結果沿用原key，不能自動重建key。部署順序、canonical payload、LINE確認前不寫入及回退限制見`docs/financial-write-safety.md`。

### Receipt import V1

登入後呼叫 `POST /api/receipt-imports`，傳入 `{qr_payload, input_method}`；`input_method` 為 `qr_camera` 或 `qr_image`。只接受台灣左側 QR，後端驗證日期、號碼、賣方統編與含稅總額。此解析不驗證發票真偽或作廢狀態，原文與圖片不保存。

成功 `data` 為 `{receipt, duplicate}`。receipt 包含 `id`、`invoice_number`、`issued_on`、`seller_identifier`、`total_amount`、`currency`、nullable `merchant_name`、`status` 與 nullable `transaction_id`。狀態為 `pending`／`linked`／`ignored`；精確身分為使用者＋號碼＋日期＋賣方統編，與來源無關。

`GET /api/receipt-imports/:id/matches?merchant=...` 回傳 `{receipt, candidates}`，最多五筆；candidate 含 `id/date/amount/currency/title/merchant/reasons`。限本人未刪除的日常支出、同金額同幣別、日期前後一天且尚未連結發票，永遠不自動合併。

`POST /api/receipt-imports/:id/resolve` 傳入 `action`：

- `create`：必填 `item`、`budget_category`，可填 `account_id`、`merchant`、`description`；日期、金額、幣別由 receipt 固定，交易與連結原子提交。
- `link`：傳入 `transaction_id`，必須為目前候選；不覆寫既有交易。
- `ignore`：保留發票但不新增交易。
- `reopen`：將略過項目回到 pending。

回傳 `{receipt, replayed}`；linked receipt 重送回傳 `replayed=true`。原交易軟刪除後重新掃描／處理會回到 pending，重新建立使用新的伺服器 request ID。所有 endpoint 成功 200、輸入或存取錯誤 400、未登入 401、未預期錯誤 500（不回傳內部細節）。

需先部署 migration `20261008_0016`，再部署 backend/frontend。V1 不含批次確認或載具 API。

- 本文件涵蓋的既有欄位不得無預警改名、改型別或改變 nesting。
- 新增 optional 欄位屬向後相容；移除欄位、改為 required、改變金額／日期型別或更換 pagination 模式都需要獨立 migration 計畫。
- Client 對未知欄位必須容忍；對必填欄位缺失則應回報 decode error，不自行填入可能改變財務語意的預設值。
- Web 視覺重構不得改變上述資料口徑。iOS client 應先依此 contract 建立 DTO 與 decode tests，再開始寫入流程。

## R04：TWD 個人報表限制

月報交易投影、dashboard、預算摘要、月支出、收支摘要、分類時間序列與超支警告，
對查詢範圍內應納入但換算本幣不是 TWD 的金額回 400 與明確提示，不回錯誤總額。
由共用錯誤處理回覆的入口另含 `code=REPORT_CURRENCY_UNSUPPORTED`。
原幣不是 TWD 但已換為 TWD 不受阻擋；一般／旅行帳本不套此限制。
月份篩選在驗證前套用，cursor／limit 在驗證後套用。原始帳務不變。

## R11 旅行帳本復原與個人月報

軟刪除的帳本不出現在一般共享交易查詢。`monthly_report=true` 與首頁月報仍依使用者
偏好保留本人分攤，回傳以分攤 ID 識別的唯讀月報列，金額已是 TWD，包含日期、分類及
`is_trip_share: true`、`can_edit: false`、`can_delete: false`。分頁游標也使用分攤 ID，與排序條件一致。
擁有者復原時沿用原帳本 ID、封存狀態與成員權限，原分攤仍只計一次。

## Monthly budgets

`POST /api/budgets` 設定指定月份及分類的預算。重新設定已軟刪除的預算時，沿用同使用者、
同月份及同分類的原預算 ID，套用新金額及備註，並清除 `deleted_at` 與 `purge_after`。
成功仍回 201，`data.transaction_id` 為 `null`。預算摘要恢復顯示新設定。

## R16：建立結果隔離

交易 ID／replayed 僅從該次建立結果取得。建立帳戶／預算不代表建立交易，
相容 response 的 `data.transaction_id` 為 null，不用其他請求的結果確認 parse event。

## S4.1：交易請求指紋與公開 key 門檻（現行）

`POST /api/transactions` 必填 UUID 字串 `client_request_id`，首次成功 201、同原始意圖回放 200；
`data.transaction_id`／replayed shape 不變。不同原始 payload 回 409 與
`code=REQUEST_PAYLOAD_CONFLICT`；舊 key 無原始指紋回 409、
`code=LEGACY_REQUEST_UNVERIFIABLE`、`data.transaction_id` 供核對（僅本人）。
原交易可已被編輯／刪除，不以目前內容冒充原始請求，不自動產生新 key。
公開 HTTP 缺少／空白／非字串／不合法 UUID key 回 400 且零財務寫入，不由伺服器產生 key。
internal manager 保留無 key 相容呼叫，不承諾該路徑冪等。Web 恢復與必填切換已有本機證據，正式部署驗收未完成。

S4.1 Web client 現已在 POST 前保存 owner／daily或trip scope 的原payload/key，未知
結果以原資料重試。收到 legacy 409 時顯示既有 ID，只有明確核對後才清本機pending，
不對既有交易發出修改／刪除／再次建立。公開 API key 已切為必填；部署前須協調
所有寫入client。不能將已更新Web視為所有部署中的舊client均已更新。

更新後Web另提供 `X-Nomica-Request-Owner`（來自該pending初始化的auth/me user ID）。
Header存在且不同於真正token/session actor時，交易POST優先回409
`REQUEST_OWNER_CHANGED`並rollback；header不授予任何身份或資源權限。
無header的既有client仍相容；公開key必填已實作，部署驗收尚未完成。

### 部署相容性：必填交易key

本批HTTP契約改變，舊client缺key將得到400，不能由Backend自動補key來偽裝冪等。
先確認DB已有financial_commands（0017；目前本機chain head0019），協調發布帶key
的Web／其他寫入client，再切換Backend並驗收。過渡期間維持財務寫入關閉或限制於
已確認的新client；沒有在本輪操作正式部署、DB升級或對外開放。此批不新增migration。
owner header不符的409優先於missing-key400，避免誤把原帳號的未知請求解除。


## 旅行共用匯率

- `GET /api/trips/<id>/exchange-rates`：成員可讀，回傳基準幣別、各外幣的旅行匯率與內建參考匯率、已記支出筆數、是否因還款紀錄而鎖定、最近 10 筆變更。
- `PUT /api/trips/<id>/exchange-rates/<currency>`：僅旅行擁有者；body `{rate}`，大於 0、最多 8 位小數。只影響之後新增的支出，回傳尚有幾筆已記支出匯率不同。
- `GET /api/trips/<id>/exchange-rates/<currency>/apply-preview`：僅擁有者；回傳筆數、總額變化、每位旅伴的結算變化與會連動調整的付款人帳戶。
- `POST /api/trips/<id>/exchange-rates/<currency>/apply`：僅擁有者；body `{confirm:true}`。整批重存已記支出，任一筆失敗則全部不變；已有還款紀錄時回 400。
- 新增或編輯旅行支出未提供 `exchange_rate` 時，順序為：旅行匯率 → 內建參考匯率 → 拒絕（不會默認為 1）。
