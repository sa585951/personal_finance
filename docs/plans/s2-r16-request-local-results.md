# S2.3 R16：請求結果隔離補漏

Spec：原 S2.3，直接回傳交易 ID／replayed，不依賴共享 manager 可變欄位。
R03 完成不等於 S2 全部完成。本項核對原計畫後補回，優先於進入 S4。
Constraints：保留舊二值 unpack 相容性與舊測試 helper；已開放呼叫方不能再讀 last_*。
資產／預算不建立交易，不得回傳或確認別筆交易 ID。LINE 自然語言仍走既有確認草稿。

## Task 1: 直接回傳 request-local 建立結果
1. 共用 BudgetManager／scoped Session，兩執行緒在 add_transaction 返回前同步，驗證 ID／replayed 不串錯。
   Expected: 現況新建／重播與新建混合案例 RED。
2. HTTP 資產／預算建立不得回傳先前交易 ID。
   Expected: 現碼回 stale ID，RED。
3. 最小相容 result 物件維持兩值 unpack，附自身 transaction_id／replayed；Service 直接取該結果。
   移除不建立交易的 endpoint 的共享結果依賴；LINE 相容 helper 改為明確傳入 result，更新 test doubles 與真實事件狀態驗收。
   Expected: 新案例及既有 Web／LINE／receipt regression GREEN。
4. 專用 runner tests -q 全套通過後更新狀態、commit、task-done。
Review Focus：共用 Manager 下結果確實 request-local；重播狀態正確；舊內部二值 unpack 不破壞；非交易建立不能關聯 stale parse event；不開放 LINE／AI。
