# S1 安全邊界修補

## R01：旅行列表與個人月報查詢

`GET /api/transactions` 不接受同時提供有效 `trip_id` 與
`monthly_report=true`，回應 400。旅行列表與個人月報分別沿用既有查詢，
避免旅行列表分支引用未 join 的 `transaction_splits`。

回歸包含 Manager 的查詢前拒絕、Flask API 400，以及兩條正常查詢的
PostgreSQL SQL 編譯檢查。這些檢查不等同正式資料影響或完整資料隔離驗收。
本項不修改歷史帳務、不需要 migration。

## R02 / U06：旅行對話框純文字輸出

邀請、結算摘要與 CSV 的手動複製備援，以 DOM textarea 的 `value`
設定內容；刪除對話框以 `text` 顯示共享名稱。不得將使用者文字插入 HTML。
`test:ui` 使用真實 SweetAlert 與 TripsView methods，驗證 textarea 跳脫字串及
惡意旅行名稱不產生 img/svg 或執行事件，並確認取消不執行刪除。
本項只處理 HTML 邊界；CSV 公式安全仍獨立追蹤 R25。
