# S3 R04：TWD 報表拒絕混幣

Spec：使用者已確認「先限制 TWD 報表，遇非 TWD 分攤明確報錯，保留原始資料且不靜默漏算」。
對照 `docs/finance-contract.md` 的 active member、include、本人 split、未刪除條件。

Global constraints：保留 worktree／分支，不 push／merge／PR；只用已同意的專用測試 DB。
不改交易原幣、旅行結算幣別、歷史資料或匯率；不新增報表換匯能力。不跳過 R04 執行 R05。

## Task 1: 報表入口統一拒絕非 TWD 金額

Interfaces：monthly transaction projection → dashboard／income-expense；monthly expenses → budget／月報；category-over-time → 歷史圖表。

1. 新增真實 DB regression：上述入口對應納入的 USD base split 都拋驗證錯誤；分頁不可隱藏異幣。
   Expected: 新增拒絕案例先 RED，原因為沒有拋錯。
2. 保留正常 TWD、非 TWD 原幣但已換成 TWD、exclude、無本人 split、已刪除、不同月份／使用者的案例。
   Expected: 不相關資料不誤擋；交易／分攤資料保持原樣。
3. 僅在個人報表路徑增加 TWD 驗證，保持一般／旅行帳本原幣可讀。
   Expected: 新 regression GREEN；API 清楚回 400 且不回錯誤總額。
4. 執行 `python3 /private/tmp/nomica-s3-r04-review-20261030/run.py tests -q`。
   Expected: 全套通過且零 skip；記錄實際數量，不預填承諾。
5. 更新財務／API 契約及問題狀態，驗證後 commit。

Review Focus：分攤 base_currency 與 original share_currency 不得混淆；依納入資格與篩選範圍判斷；分頁不得繞過；新讀入的異幣也不得通過聚合；一般帳本可讀；不更新任何歷史金額。
