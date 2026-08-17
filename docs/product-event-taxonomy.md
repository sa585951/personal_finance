# Nomica Product Event Taxonomy

## 文件狀態

- 版本：M0 V1
- 生效日期：2026-08-17
- 目的：定義跨 Web、LINE、PWA 與未來 iOS 共用的產品量測語言

本文件只定義事件契約。目前不指定 PostHog、Firebase 或其他 analytics provider，也不要求在 M0 接入 SDK。

## 隱私原則

Analytics event 與 properties 禁止包含：

- 使用者輸入的自然語言原文。
- 交易 title、merchant 或 description。
- 帳戶名稱、旅行名稱或目的地自由文字。
- 精確金融金額、餘額、匯率或投資市值。
- Email、LINE user id、Apple subject、Google subject 或邀請 token。
- JWT、session id、authorization header 或任何 secret。

允許的共同 properties：

| Property | 範例 | 規則 |
| --- | --- | --- |
| `platform` | `web`, `line`, `ios` | 固定 enum |
| `environment` | `production`, `staging` | production analytics 不送 development event |
| `entry_method` | `manual`, `ai`, `quick_action` | 不帶輸入原文 |
| `currency_code` | `TWD`, `JPY` | 只表示幣別，不帶金額 |
| `is_trip` | `true` | boolean |
| `member_count_band` | `1`, `2-4`, `5-10`, `11+` | 不送完整成員資料 |
| `occurred_at` | ISO timestamp | 由 analytics SDK 或 server 產生 |

若需要關聯同一使用者，只能使用 analytics 專用 opaque id；不得直接送第三方 provider identity。服務端內部 audit log 不屬於本文件範圍。

## 命名規則

- 使用 lowercase snake_case。
- 事件描述已完成的事實，不描述按鈕文字。
- 同一個 business outcome 只定義一個 canonical event。
- 嘗試、失敗與完成若都需要量測，使用 `_started`、`_failed`、`_completed` 後綴。
- 金融寫入事件只在 DB commit 成功後送出。
- retry 或重複 request 不可重複計入完成事件。

## M0 核心事件

### `signup_completed`

使用者首次建立 Nomica user 且登入流程完成。

允許 properties：

- `platform`
- `provider_type`: `line`, `apple`, `google`
- `is_invite_flow`: boolean

不得帶 provider user id 或 email。

### `first_account_created`

使用者成功建立人生週期中的第一個 active account。

允許 properties：

- `platform`
- `account_type`
- `currency_code`
- `tracks_balance`: boolean

不得帶帳戶名稱或初始餘額。

### `first_transaction_created`

使用者成功建立第一筆日常 Income 或 Expense。

允許 properties：

- `platform`
- `transaction_type`: `income`, `expense`
- `entry_method`
- `has_linked_account`: boolean
- `currency_code`

不得帶金額、分類自由文字、merchant 或 description。

### `trip_created`

成功建立一趟 Trip。

允許 properties：

- `platform`
- `base_currency_code`
- `default_currency_code`
- `duration_band`: `single_day`, `2-3`, `4-7`, `8+`

不得帶旅行名稱、目的地或日期原值。

### `trip_invite_sent`

成功建立或分享旅行邀請。

允許 properties：

- `platform`
- `inviter_role`
- `member_count_band`

不得帶 invite token 或邀請對象 identity。

### `trip_invite_accepted`

登入使用者成功加入旅行。

允許 properties：

- `platform`
- `member_role`
- `member_count_band`

### `shared_expense_created`

成功建立至少兩個 Share 的旅行 Expense。

允許 properties：

- `platform`
- `entry_method`
- `split_method`: `equal`, `custom`
- `currency_code`
- `member_count_band`
- `payer_is_current_user`: boolean
- `has_linked_account`: boolean

不得帶 Payment、Share 或換算金額。

### `settlement_completed`

成功確認一筆 Group Settlement。

允許 properties：

- `platform`
- `actor_role`: `owner`, `payer`
- `currency_code`
- `is_partial`: boolean
- `account_posting_mode`: `group_only`, `own_side_posted`

M0 現行固定為 `group_only`；`own_side_posted` 只在 M3 正式實作後使用。

### `trip_report_included`

登入成員將自己的 `monthly_report_preference` 明確改為 `include`。

允許 properties：

- `platform`
- `member_role`
- `was_pending`: boolean

## 後續候選事件

以下不在 M0 第一版接入範圍，只保留命名方向：

- `universal_add_started`
- `universal_add_completed`
- `analysis_viewed`
- `trip_closeout_completed`
- `settlement_account_posted`
- `account_reconciliation_checked`
- `pwa_installed`
- `session_restored`

新增事件前必須先回答：它會支持哪一個產品決策；若不能支持明確決策，就不應蒐集。

## 實作邊界

- M0 不接 analytics SDK、不新增資料表。
- M1 前先決定 event dispatcher 介面與 production consent／privacy 策略。
- Analytics 失敗不得阻止財務 transaction commit。
- 財務寫入完成事件應具備冪等識別，但識別值不得以明文送往未核准的第三方。
