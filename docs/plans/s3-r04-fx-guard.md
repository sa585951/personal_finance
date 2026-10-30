# S3 R04 小批次：缺少匯率不得當作 1

延續已確認 S3，不重排 Roadmap。本輪僅此一個 task。

Spec：既有對話確認的 R04 驗收「缺匯率不得默認為 1」；財務名詞依
`docs/finance-contract.md`，其未完整描述匯率規則的部分以該已確認要求為準。

Global Constraints：不改歷史帳務、schema、預設匯率表、月報、R05／R06／R07、
前端或已完成 S1／S2。只在本輪獨立 DB 測試，不能接觸正式／既有 DB。

## Task 1: 拒絕未知跨幣別的隱含等值換算

Interfaces：BudgetManager._default_exchange_rate → add_transaction / update_transaction。

1. 在本輪專用 PostgreSQL 執行既有 `tests` baseline。
   Expected: 475 passed。
2. 新增 `tests/test_exchange_rate_guard.py`，以真實 Manager / DB 驗證：
   未知 GBP→TWD 且未傳匯率的新增與改幣別均拒絕，交易／餘額／movement 不變。
   Expected: 兩項 regression 因沒有拒絕而失敗（RED）。
   另保留同幣別 1、既有 USD→TWD 預設值、GBP 顯式匯率的成功契約。
3. 僅修補未知 pair fallback，回 ValueError；同幣別及明確匯率維持既有行為。
   Expected: `tests/test_exchange_rate_guard.py` 全部通過（GREEN）。
4. 全套驗證：本輪安全 runner 執行 `tests -q`。
   Expected: 全部通過，零 skip；無 migration，沒有正式資料異動。
5. 更新本輪執行紀錄，核對 diff，以 `fix(finance): reject missing cross-currency exchange rates` commit。
   Task completion command：同一步驟 4 的安全 runner。

Review Focus：是否從兩個寫入入口阻止 fallback；錯誤前是否已留下持久副作用；
同幣別與顯式匯率是否維持；是否誤宣告 R04 月報混幣或 R05 編輯保留匯率已完成。
