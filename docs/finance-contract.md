# Nomica Finance Contract

## 文件狀態

- 版本：M0 V1
- 生效日期：2026-08-17
- 適用端：Web、LINE、未來 iOS 與後端 API
- 目的：固定 Nomica 的財務語意、統計口徑與帳戶 ownership 邊界

本文件同時描述「現行已實作行為」與「M3 Ledger Correctness 目標」。M3A 至 M3D 已完成第一版；legacy schema 收斂仍是後續目標。

## 核心不變條件

```text
Payment != Expense
Settlement != Income / Expense
Transfer != Income / Expense
Adjustment != Income / Expense
```

- `Payment` 回答誰先付款、哪個帳戶實際移動多少。
- `Expense` 回答某位使用者最後應負擔多少。
- `Settlement` 清償成員間的 Receivable／Payable，不產生新的收入或支出。
- `Transfer` 只移動同一使用者擁有的帳戶資金。
- `Adjustment` 校正帳戶快照，不代表賺到或花掉一筆錢。

任何 Web、LINE 或 iOS 功能都不得以顯示方便為由破壞上述關係。

## 名詞定義

### Payment

實際由付款人先支付的金額。若付款人選擇自己的追蹤帳戶，該帳戶依整筆 Payment 產生 movement。

例如四人餐費 TWD 12,000 由我刷卡：

```text
Payment = 12,000
我的信用卡 movement = -12,000
```

Payment 本身不能直接推論我的最終 Expense。

### Expense

歸屬於使用者個人統計的實際負擔。

- 日常交易：Expense 等於該筆支出金額。
- 旅行交易：Expense 等於目前使用者的 `transaction_splits.converted_share_amount`。
- 旅行成員的 `monthly_report_preference` 必須為 `include` 才納入個人月報。
- 沒有目前使用者 split 的旅行交易不納入，不 fallback 成整筆 Payment。

### Share

Shared Expense 中某位旅行成員應負擔的金額。所有有效 Share 合計必須等於該筆 Payment 的原幣金額；換算誤差依既有尾差規則分配。

外部旅伴可以有 Share，但沒有 Nomica 私人帳戶 movement。

### Receivable

某成員替別人代墊後應收回的金額。它是成員間債權，不是新的 Income。

### Payable

某成員尚需支付給其他成員的金額。它是成員間債務，不是新的 Expense。

### Settlement

清償 Receivable／Payable 的群組紀錄。

- M0 現況：只更新旅行分帳淨額，不異動任何私人帳戶。
- M3 目標：可由付款方與收款方各自為自己的 settlement side 建立 account entry。
- Settlement 無論是否連動帳戶，都不納入 Income／Expense。

### Transfer

同一使用者擁有的兩個帳戶之間移動資金。

```text
來源帳戶 = -source amount
目標帳戶 = +target amount
Income / Expense = 0
```

信用卡繳款屬於 Transfer：銀行帳戶減少、信用卡負數債務回補，不建立支出。

### Account Movement

會改變某個帳戶餘額的帶正負號變化。Movement 來源可包含：

- 日常或旅行 Payment。
- Income transaction。
- Transfer source／target。
- M3 Settlement account entry。
- Adjustment（M3B 已完成）。

Account Movement 與月報分類是兩套不同維度。

### Adjustment

使用者為了讓 Nomica 餘額與實際帳戶一致所做的校正。

- M3B 現況：帳戶餘額校正會建立 `account_adjustments`，保存 delta、校正前後餘額、原因與時間，再於同一 DB transaction 更新 `accounts.balance`。
- 舊的 `update_balance`／`adjust_asset_balance` 相容入口也會導向 Adjustment，不再直接覆寫快照。
- Adjustment 永遠不計入 Income／Expense。

### Balance Anchor

某一時間點經確認的帳戶餘額基準。

- M3A 現況：新帳戶會建立初始 Anchor；既有追蹤餘額帳戶由 migration 以當前快照建立 `migration` Anchor。
- M3D migration `20260821_0013` 會為既有追蹤帳戶建立新的 `reconciliation_baseline`，不改寫餘額；CLI 只重播此 baseline 後留下的 movement。

## 帳戶 movement 符號

| 事件 | 帳戶 movement |
| --- | ---: |
| 支出使用追蹤帳戶 | `-amount` |
| 收入存入追蹤帳戶 | `+amount` |
| Transfer 來源 | `-source_amount` |
| Transfer 目標 | `+target_amount` |
| Settlement incoming（M3） | `+amount` |
| Settlement outgoing（M3） | `-amount` |
| Adjustment（M3B 已完成） | `amount_delta` |

信用卡帳戶允許負數；其他帳戶依目前規則不得因一般支出或轉帳變成負數。

## 月報口徑

### 日常交易

```text
Daily Income = type=income、trip_id IS NULL 的 converted_amount
Daily Expense = type=expense、trip_id IS NULL 的 converted_amount
```

### 旅行交易

旅行支出只在以下條件全部成立時納入個人月報：

1. 使用者是 active TripMember。
2. `monthly_report_preference = include`。
3. 該交易存在此 TripMember 的 split。
4. 交易未刪除且 `type = expense`。

納入金額為該使用者的 `converted_share_amount`，不是 Payment 全額。

### 永不納入月報

- Transfer。
- Group Settlement。
- M3 Settlement account entry。
- Adjustment。
- Asset Allocation cost entry／snapshot。

## Balance Contract

### M3D 現況

`accounts.balance` 仍是可直接讀取的目前快照。交易與 Transfer 在同一應用層操作中同步更新此欄位與 append-only `account_movements`；Group Settlement 本身不更新帳戶。

使用者校正餘額時必須建立 Adjustment；私人 Settlement posting／reversal 保存在 `settlement_account_entries`。Reconciliation 從最新 Anchor 開始加總 Transaction／Transfer movement、Settlement account entry 與 Adjustment，不猜測 Anchor 前的 legacy 歷史。

### Expected Balance 公式

```text
Expected Balance
= Latest Anchor balance
+ Transaction movements after anchor
+ Transfer movements after anchor
+ Settlement account entries after anchor
+ Adjustments after anchor
```

規則：

- `accounts.balance` 保留為目前餘額快照，不改成完全 Event Sourcing。
- Anchor 建立前的歷史 movement 不重算，避免猜測舊帳戶初始餘額。
- Reconciliation 只回報 `Expected Balance - Stored Balance`，不得自動覆寫。
- 使用者透過 Adjustment 處理差異。
- 同一業務操作的 ledger record 與 `accounts.balance` 更新必須在同一 DB transaction。
- `account_movements` 只記錄 Transaction 與 Transfer 的帳戶效果；Settlement 與 Adjustment 保留各自的 append-only domain table，避免混淆業務語意。
- CLI 是 read-only 工具；`--fail-on-issues` 只改變 exit code，不會寫入任何帳戶資料。

## Settlement Ownership Contract

### Group Settlement

- Trip Owner 或該筆建議的付款方本人可確認 Group Settlement。
- Trip Owner 或原結算記錄者可撤銷目前 Group Settlement。
- 這些權限只管理群組債務狀態，不代表能操作任何成員的私人帳戶。

### Private Account Posting（M3）

- Trip Owner 不可選擇、指定或異動其他使用者的私人帳戶。
- 使用者只能為自己的 settlement side 選擇本人帳戶。
- 收款方只可建立自己的 incoming entry。
- 付款方只可建立自己的 outgoing entry。
- 外部旅伴 `user_id IS NULL`，不得建立 Account Movement。
- V1 帳戶幣別必須等於 Settlement 幣別；不符合時只能選擇不追蹤。
- `(settlement_id, user_id)` 必須唯一，重複 request 不可二次異動餘額。
- Reversal 只能執行一次，且只能反轉原 entry 的 movement。

### M3C 實作狀態

- `settlement_account_entries` 保存每位使用者自己的 incoming／outgoing movement、posting 前後餘額及一次性 reversal 前後餘額。
- 確認 Group Settlement 時可不選帳戶；付款方與收款方也可在已確認結算中，分別補記自己的私人帳戶。
- 帳戶必須屬於目前使用者、啟用餘額追蹤且幣別與 Settlement 相同。
- `(settlement_id, user_id)` 唯一；相同帳戶重送視為 replay，不重複異動餘額。
- 有尚未反轉的私人 posting 時，Group Settlement 不可撤銷，避免 Trip Owner 間接異動其他成員的私人帳戶。
- Settlement posting 與 reversal 會顯示於帳戶活動，但不建立 Transaction，也不進 Income／Expense、預算或月報。

## 標準案例

| 情境 | 帳戶變化 | 個人月報變化 | 實作狀態 |
| --- | ---: | ---: | --- |
| 日常刷卡支出 1,000 | 信用卡 `-1,000` | Expense `+1,000` | 已完成 |
| 銀行繳信用卡 1,000 | 銀行 `-1,000`、信用卡 `+1,000` | `0` | 已完成（Transfer） |
| 我替四人刷 12,000、平均分攤 | 我的帳戶 `-12,000` | 我的 Expense `+3,000` | 已完成，需選擇納入月報 |
| 朋友還我 9,000，只確認群組結算 | `0` | Income／Expense `0` | M0 現況 |
| 朋友還我 9,000 並由我入帳 | 收款帳戶 `+9,000` | Income／Expense `0` | M3 目標 |
| 手動校正 +500 | 帳戶 `+500` | Income／Expense `0` | M3B 已完成（Adjustment） |

## API 與 UI 用詞

- 顯示整筆代墊時使用「你付款」或「整筆付款」，不可稱為「你的支出」。
- 顯示個人統計時使用「你的負擔」或「我的分攤」。
- Settlement 操作使用「確認還款／收款」時，必須說明是否只是群組確認或也會更新自己的帳戶。
- 信用卡繳款入口應導向帳戶互轉，不建立新的 Expense。
- LINE Shared Expense 未來必須經過 Parse、Preview、Confirm、Commit，不可直接 auto-commit。

## 實作邊界

M0 已建立共同語言與 characterization tests；M3A 至 M3D 已新增 Anchor、Adjustment、Settlement Account Entry、Transaction／Transfer movement ledger 與 read-only Expected Balance CLI。M3E 保留 legacy goals 與舊 schema 使用情況收斂。
