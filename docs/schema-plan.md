# Schema Plan Draft

此文件是新版資料庫 schema 的討論草稿，暫時不代表已套用，也不會直接操作 Supabase production。

## 目前決策

- 舊資料可全部刪除，不需要為舊交易寫複雜 migration。
- Production 目前使用 Supabase PostgreSQL；本地開發使用 Docker / OrbStack PostgreSQL。
- 新版 schema 以「日常記帳 + 旅行帳本 + 多幣別 + 輕量分帳 + 跨平台 AI 記帳」為核心。
- 不做股票與投資資產管理。
- 使用內部 UUID 作為所有主要資料表主鍵。
- LINE / Google / Apple 等第三方登入資訊拆到 `user_identities`。
- LINE Bot 語意記帳保留，但 AI parser 要抽成跨平台服務，未來 Web / PWA / iOS 共用。
- `assets` 改為 `accounts`，表示付款來源或帳戶，不表示投資資產。
- `accounts` 使用 optional balance tracking。
- 每趟 trip 建立時自動建立 owner trip member。
- 外部旅伴可作為付款人與分攤人，未來可透過邀請綁定真實 user。
- 分帳明細落資料庫；第一版支援平均分攤，除不盡餘數給付款人。
- `settlements` 提前納入 MVP，用於確認旅伴間已還款；不連動個人帳戶餘額。
- 交易匯率方向固定為 `1 original_currency = exchange_rate base_currency`。
- 轉帳匯率方向固定為 `target_per_source_rate = target_amount / source_amount`。
- `exchange_rates` 先預留；MVP 可手動輸入匯率，後續再串 API。
- 導入 Alembic；新版 schema 定案後所有 schema 變更透過 migration 管理。

## 正規化原則

- 核心表使用 UUID 主鍵，避免外部登入 ID 綁死資料模型。
- 外部身份拆到 `user_identities`，支援多 provider 綁定同一 user。
- 多值資料拆表，例如 trip members、transaction splits、categories。
- 匯率與換算後金額屬於交易當下快照，保存在交易 / split / transfer 中，避免日後匯率更新改變歷史結果。
- 報表、月報、旅行結算原則上由交易、分帳、預算計算得出；必要時未來再加 snapshot。
- 代碼型欄位先用受控字串，後續可改 PostgreSQL enum 或 lookup table。
- MVP 避免過度抽象，但不犧牲未來擴充必要的關聯設計。

## 共用規則

- 金額欄位使用 `Numeric(18, 4)`。
- 匯率欄位使用 `Numeric(18, 8)`.
- 系統時間欄位 `created_at` / `updated_at` 使用 UTC。
- 交易歸屬使用 `transaction_date`，不是 `created_at`。
- MVP 幣別小數位：`TWD=0`、`JPY=0`、`KRW=0`、`USD=2`、`EUR=2`。
- 兩段式刪除：可復原資料使用 `deleted_at` / `purge_after`；不再使用但需保留歷史引用的資料使用 `archived_at` 或 `is_active=false`。

## 候選資料表

### users

使用者基本資料與偏好設定。

```text
id uuid pk
display_name
email nullable
avatar_url nullable
locale
timezone
base_currency fk -> currencies.code
created_at
updated_at
deleted_at nullable
purge_after nullable
```

決策：

- `base_currency` 初期預設 `TWD`。
- 未來可依瀏覽器語系 / App locale / 使用者設定建議幣別，但 MVP 以手動設定為準。

### user_identities

外部登入 provider 與使用者對應。

```text
id uuid pk
user_id uuid fk -> users.id
provider
provider_user_id
provider_email nullable
provider_display_name nullable
created_at
updated_at
```

約束：

- `provider + provider_user_id` unique。

決策：

- 第一版即建立此表，不把 LINE user id 放在 users 主表。
- `provider` 初期支援 `line`，未來支援 `google`、`apple`、`email`。

### currencies

幣別 lookup table，用於格式化、分帳 rounding 與 FK 約束。

```text
code pk
name
symbol
minor_unit
is_active
created_at
updated_at
```

初始資料：

```text
TWD | New Taiwan Dollar | NT$ | 0
JPY | Japanese Yen      | ¥   | 0
KRW | Korean Won        | ₩   | 0
USD | US Dollar         | $   | 2
EUR | Euro              | €   | 2
```

### accounts

付款來源或帳戶。不做投資資產。

```text
id uuid pk
user_id uuid fk -> users.id
name
type
currency fk -> currencies.code
track_balance boolean
balance numeric(18,4) nullable
is_active boolean
archived_at nullable
created_at
updated_at
deleted_at nullable
purge_after nullable
```

規則：

- `track_balance=true`：現金、銀行、電子錢包、預付卡。
- `track_balance=false`：信用卡、Apple Pay / LINE Pay 通道、朋友代墊、公司卡。
- 只有 `track_balance=true` 的 accounts 可做 transfers。
- `type` 初期支援 `cash | bank | credit_card | e_wallet | prepaid_card | external | other`。

### categories

系統預設 + 使用者自訂分類，支援 parent / child。

```text
id uuid pk
user_id uuid nullable fk -> users.id
parent_id uuid nullable fk -> categories.id
kind
scope
code
name
icon nullable
color nullable
is_system boolean
is_active boolean
sort_order integer
created_at
updated_at
deleted_at nullable
purge_after nullable
```

規則：

- `user_id=null` 是系統分類；`user_id!=null` 是使用者自訂分類。
- `parent_id=null` 是大分類；`parent_id!=null` 是子分類。
- `kind = expense | income | both`，MVP 主要用 `expense` / `income`。
- `scope` MVP 使用 `transaction`，未來可擴充。
- MVP UI 先使用大分類，子分類先預留。
- 未來多語系可新增 `category_translations`。

系統支出大分類：

```text
food, transport, lodging, shopping, entertainment, medical,
daily, subscriptions, fees, other
```

系統收入大分類：

```text
salary, bonus, interest, gift, reimbursement, other_income
```

### trips

旅行帳本。

```text
id uuid pk
owner_user_id uuid fk -> users.id
name
destination nullable
start_date
end_date
timezone
base_currency fk -> currencies.code
default_currency fk -> currencies.code
status
include_in_monthly_report boolean
created_at
updated_at
deleted_at nullable
purge_after nullable
archived_at nullable
```

規則：

- `base_currency` 是結算幣別。
- `default_currency` 是旅行預設交易幣別。
- 每筆交易仍可使用不同 `original_currency`。
- `status` 初期支援 `active | archived`。

### trip_members

旅行成員，同時支援分帳成員與未來共同編輯權限。

```text
id uuid pk
trip_id uuid fk -> trips.id
user_id uuid nullable fk -> users.id
display_name
role
status
created_at
updated_at
removed_at nullable
deleted_at nullable
purge_after nullable
```

規則：

- 建立 trip 時自動建立 owner member。
- `user_id=null` 表示尚未綁定真實 user 的外部旅伴。
- 外部旅伴可作為付款人與分攤人。
- 未來邀請加入後，可把原本 external member 綁定到真實 `users.id`。
- `role = owner | editor | viewer`。
- `status = active | invited | removed`。

### transactions

日常與旅行交易主表。

```text
id uuid pk
user_id uuid fk -> users.id
trip_id uuid nullable fk -> trips.id
account_id uuid nullable fk -> accounts.id
category_id uuid fk -> categories.id
paid_by_member_id uuid nullable fk -> trip_members.id
transaction_date date
transaction_time time nullable
timezone
type
merchant nullable
title
description nullable
original_amount numeric(18,4)
original_currency fk -> currencies.code
exchange_rate numeric(18,8)
converted_amount numeric(18,4)
base_currency fk -> currencies.code
created_at
updated_at
deleted_at nullable
purge_after nullable
voided_at nullable
void_reason nullable
```

規則：

- `type = expense | income | transfer | adjustment`，`refund` deferred。
- `merchant` 是店家 / 平台 / 服務商。
- `title` 是交易名稱或品項，MVP 必填。
- `description` 是備註。
- `converted_amount = original_amount * exchange_rate`。
- `exchange_rate` 表示 `1 original_currency = exchange_rate base_currency`。
- 日常交易與旅行交易都使用同一組多幣別欄位。
- 旅行交易可用 `paid_by_member_id` 指定付款人；付款人可為外部 member。

### transaction_splits

分帳明細。每個參與分攤的人一筆。

```text
id uuid pk
transaction_id uuid fk -> transactions.id
trip_member_id uuid fk -> trip_members.id
split_method
share_amount numeric(18,4)
share_currency fk -> currencies.code
exchange_rate numeric(18,8)
converted_share_amount numeric(18,4)
base_currency fk -> currencies.code
created_at
updated_at
```

規則：

- MVP `split_method = equal`。
- 沒參與分攤的人不建立 split。
- 平均分攤除不盡時，依幣別 `minor_unit` rounding，餘數分配給付款人。
- split 保存實際分攤後金額，避免日後成員或匯率變動影響歷史結果。

### transfers

帳戶間轉帳 / 換匯 / 儲值。

```text
id uuid pk
user_id uuid fk -> users.id
trip_id uuid nullable fk -> trips.id
source_account_id uuid fk -> accounts.id
target_account_id uuid fk -> accounts.id
source_amount numeric(18,4)
source_currency fk -> currencies.code
target_amount numeric(18,4)
target_currency fk -> currencies.code
target_per_source_rate numeric(18,8)
fee_amount numeric(18,4) nullable
fee_currency fk -> currencies.code nullable
transfer_date date
note nullable
created_at
updated_at
deleted_at nullable
purge_after nullable
```

規則：

- 轉帳獨立成表，不混入一般交易報表。
- `target_per_source_rate = target_amount / source_amount`。
- source / target accounts 都必須 `track_balance=true`。

### budgets

日常分類預算與旅行總預算。

```text
id uuid pk
user_id uuid fk -> users.id
trip_id uuid nullable fk -> trips.id
scope
period_start date
period_end date
category_id uuid nullable fk -> categories.id
amount numeric(18,4)
currency fk -> currencies.code
notes nullable
created_at
updated_at
deleted_at nullable
purge_after nullable
```

MVP 支援：

- 日常月分類預算：`scope=monthly`、`trip_id=null`、`category_id!=null`。
- 旅行總預算：`scope=trip`、`trip_id!=null`、`category_id=null`。

Deferred：

- 週預算。
- 旅行分類預算。

### exchange_rates

匯率快取與建議來源。MVP 可先手動輸入匯率。

```text
id uuid pk
from_currency fk -> currencies.code
to_currency fk -> currencies.code
rate numeric(18,8)
rate_date date
source
created_at
```

規則：

- `1 from_currency = rate to_currency`。
- 交易與 split 仍保存自己的匯率快照。
- 此表只作為預設值、建議值或未來 API 快取。

### ai_parse_events

跨平台 AI 語意記帳解析紀錄。MVP 建表但不做 UI。

```text
id uuid pk
user_id uuid fk -> users.id
source
raw_input
parsed_payload jsonb nullable
confidence numeric(5,4) nullable
status
result_type nullable
result_id uuid nullable
error_message nullable
created_at
```

規則：

- `source = line_bot | web | pwa | ios`。
- `status = success | failed | confirmed | cancelled`。
- `result_type` 可為 `transaction | transfer | budget | split | none`。
- `result_id` 是 polymorphic reference，不做傳統 FK。

### attachments

附件 / 收據 / 票券 / 截圖。MVP 預留表，不做上傳 UI。

```text
id uuid pk
user_id uuid fk -> users.id
entity_type
entity_id uuid
file_url
file_type nullable
file_name nullable
created_at
deleted_at nullable
purge_after nullable
```

規則：

- `entity_type` 可為 `transaction | trip | transfer`。
- `entity_id` 是 polymorphic reference，不做傳統 FK。
- 未來可支援收據 OCR。

### settlements

旅行分帳結清 / 還款確認紀錄。MVP 支援手動確認與撤銷，不做催款、通知或多人簽核。

```text
id uuid pk
trip_id uuid fk -> trips.id
from_member_id uuid fk -> trip_members.id
to_member_id uuid fk -> trip_members.id
recorded_by_user_id uuid fk -> users.id
amount numeric(18,4)
currency fk -> currencies.code
status
note nullable
settled_at
created_at
updated_at
deleted_at nullable
purge_after nullable
```

規則：

- `from_member_id` 是付款人，`to_member_id` 是收款人。
- `amount` 使用旅行 `base_currency`。
- 確認結算只影響分帳淨額與建議結算，不異動任何 `accounts.balance`。
- MVP `status = confirmed | voided`。
- 撤銷採兩段式刪除：`status=voided`、`deleted_at`、`purge_after`。
- 未來可支援多人確認、催款通知、付款憑證附件。

## 初步關聯

```text
users
  ├─ user_identities
  ├─ accounts
  ├─ categories
  ├─ budgets
  ├─ transactions
  ├─ transfers
  ├─ ai_parse_events
  ├─ attachments
  └─ trips
       ├─ trip_members
       ├─ transactions
       │    └─ transaction_splits
       ├─ settlements
       ├─ transfers
       └─ budgets
```

## Constraints / Indexes

### Foreign keys

- 預設採保守限制：多數 FK 使用 `RESTRICT` / `NO ACTION`，避免誤刪歷史帳務。
- 明確附屬資料可 cascade：
  - `user_identities.user_id -> users.id`
  - `transaction_splits.transaction_id -> transactions.id`
- 不 cascade 歷史引用：
  - `transactions -> accounts`
  - `transactions -> categories`
  - `transactions -> trips`
  - `transactions -> trip_members`
  - `settlements -> trips`
  - `settlements -> trip_members`
  - `transfers -> accounts`
  - `budgets -> categories`

### Unique constraints

- `user_identities(provider, provider_user_id)`
- `currencies(code)`
- `exchange_rates(from_currency, to_currency, rate_date, source)`
- `categories` 使用 partial unique indexes，確保同一 user / 同一 parent / 同一 kind / 同一 scope 下 code 不重複。
- `budgets` 使用 partial unique indexes：
  - 日常月分類預算：`user_id + scope + period_start + period_end + category_id`
  - 旅行總預算：`trip_id + scope + period_start + period_end`

### Common indexes

- `transactions(user_id, transaction_date)`
- `transactions(user_id, trip_id, transaction_date)`
- `transactions(user_id, category_id, transaction_date)`
- `transactions(user_id, account_id, transaction_date)`
- `trips(owner_user_id, status)`
- `trip_members(trip_id, status)`
- `transaction_splits(transaction_id)`
- `transaction_splits(trip_member_id)`
- `transfers(user_id, transfer_date)`
- `transfers(user_id, trip_id, transfer_date)`
- `budgets(user_id, scope, period_start, period_end)`
- `budgets(trip_id, scope)`
- `ai_parse_events(user_id, created_at)`
- `ai_parse_events(source, status, created_at)`
- `attachments(entity_type, entity_id)`

## Seed Data

Initial migration 會建立必要 reference data：

- currencies: `TWD`, `JPY`, `KRW`, `USD`, `EUR`
- expense categories: `food`, `transport`, `lodging`, `shopping`, `entertainment`, `medical`, `daily`, `subscriptions`, `fees`, `other`
- income categories: `salary`, `bonus`, `interest`, `gift`, `reimbursement`, `other_income`

## Migration Rollout

1. 本地 PostgreSQL 先透過 Docker / OrbStack 啟動。
2. 導入 Alembic，建立 `initial_new_schema` migration。
3. 本地執行 migration 並寫入 seed data。
4. 跑 schema smoke tests，確認核心資料可建立。
5. API / manager 層另階段改接新版 schema。
6. 本地驗證完成前，不操作 Supabase production。
7. Supabase production 重建流程需另行確認備份、停機窗口與 migration 指令。

注意：

- `models/schema.py` 暫時保留舊表的 legacy placeholders 在獨立 `legacy_metadata`，只為了讓現有 manager/API import 不立即失敗。
- Alembic target metadata 只包含新版 MVP schema，不會建立 legacy tables。
- 下一階段需要將 manager/API 改接新版 tables 後，再移除 legacy placeholders。

## 目前暫不處理

- 投資資產與股票價格。
- 週預算。
- 旅行分類預算 UI。
- 多人即時共同編輯 UI。
- 邀請加入 trip 流程。
- 催款通知。
- 付款狀態追蹤。
- 訂閱週期管理。
- 附件上傳 UI 與 OCR。
- AI 理財建議。

## 後續才進行的事項

- 新增 manager / API。
- 清空或重建 Supabase production schema。
- 將既有前後端功能改接新版 schema。
- 設計 Supabase production 重建與部署流程。

## 已完成的 repo 對應

- `models/schema.py` 已更新為新版 MVP schema。
- `alembic/versions/20260524_0001_initial_new_schema.py` 建立初版 migration。
- `models/seed_data.py` 提供初始 currencies 與 system categories。
- `tests/test_schema_smoke.py` 提供本地 DB smoke test。
