# Nomica API Contract Baseline

本文件記錄 2026-10-07 Web／PWA 已使用、未來 iOS client 可依賴的第一版 API contract。它是既有行為的 characterization，不代表已完成公開 API versioning。

## 共通規則

- 需要登入的 endpoint 使用 session-backed JWT；Bearer token 與 HttpOnly cookie 皆由現有 Web auth 流程處理。
- UUID 以 JSON string 傳輸。
- 日期使用 `YYYY-MM-DD`；時間使用含 timezone 的 ISO 8601 string。
- 金額、匯率與換算金額目前使用 JSON number。Client 不應自行用 binary floating point 重新計算帳務結果。
- nullable 欄位保留為 JSON `null`，不以空字串代替。
- 一般成功 response 使用 `{ "success": true, "data": ... }`；寫入操作可另外包含 `message`、`replayed`。
- 一般錯誤使用 `{ "success": false, "message": "..." }`。Auth middleware 的 401 response 目前是 legacy `{ "message": "..." }`，client 應以 HTTP status 判斷 session 失效，不依賴單一錯誤文案。
- 收到 401 時，Web／iOS 必須清除失效憑證並回到登入流程；不得持續重送同一 token。

## Auth

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

- 本文件涵蓋的既有欄位不得無預警改名、改型別或改變 nesting。
- 新增 optional 欄位屬向後相容；移除欄位、改為 required、改變金額／日期型別或更換 pagination 模式都需要獨立 migration 計畫。
- Client 對未知欄位必須容忍；對必填欄位缺失則應回報 decode error，不自行填入可能改變財務語意的預設值。
- Web 視覺重構不得改變上述資料口徑。iOS client 應先依此 contract 建立 DTO 與 decode tests，再開始寫入流程。
