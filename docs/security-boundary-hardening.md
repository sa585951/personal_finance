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

## R12：Browser-bound 單次 LINE 登入

Migration `20261021_0018` 僅新增 `oauth_login_states`，不修改使用者或帳務。
state 與瀏覽器秘密各自隨機產生，DB 僅存其 SHA256；以 callback 專用的
HttpOnly、SameSite=Lax Cookie 綁定瀏覽器，10 分鐘到期。開始新登入時清除
過期登入 metadata；多分頁以最後一次登入的 Cookie 為準，舊分頁須重新開始。

callback 透過單一條件 UPDATE 消耗 state 並先 commit，再交換 Provider token；
即使交換失敗也不能重放，須重新登入。ID token 另驗證對應 nonce；交換設 10 秒 timeout。
Auth 回應禁止快取／Referrer，錯誤不輸出 Provider 或 DB 詳情。

回歸包含不符／缺少 Cookie、過期／竄改／重放、nonce 與 HTTP 交換邊界，
以及隔離 PostgreSQL 多連線僅一次消耗、跨 Session 保留狀態和含帳務 0017 升級。
Provider 使用替身，不等於真實 LINE 登入／手機驗收。
