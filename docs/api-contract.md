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
  "session_id": "uuid"
}
```

`provider` 與 `session_id` 在正式 session response 中存在。Dev auth bypass 只保證 `user_id` 與 `name`，不得作為正式 client contract。

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

## R16：建立結果隔離

交易 ID／replayed 僅從該次建立結果取得。建立帳戶／預算不代表建立交易，
相容 response 的 `data.transaction_id` 為 null，不用其他請求的結果確認 parse event。

## S4.1：交易請求指紋（Backend 批次）

`POST /api/transactions` 帶 client_request_id 時，首次成功 201、同原始意圖回放 200；
`data.transaction_id`／replayed shape 不變。不同原始 payload 回 409 與
`code=REQUEST_PAYLOAD_CONFLICT`；舊 key 無原始指紋回 409、
`code=LEGACY_REQUEST_UNVERIFIABLE`、`data.transaction_id` 供核對（僅本人）。
原交易可已被編輯／刪除，不以目前內容冒充原始請求，不自動產生新 key。
本批 key 仍 optional；無 key 不承諾冪等。client 恢復與必填切換驗收尚未完成。

S4.1 Web client 現已在 POST 前保存 owner／daily或trip scope 的原payload/key，未知
結果以原資料重試。收到 legacy 409 時顯示既有 ID，只有明確核對後才清本機pending，
不對既有交易發出修改／刪除／再次建立。公開 API key 目前仍optional；必填切換待
相容性決策與部署驗收，不能將已更新Web視為所有舊client均已更新。
