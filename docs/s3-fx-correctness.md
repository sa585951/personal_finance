# S3 匯率與月報正確性：小批次紀錄

## R04 第一批：缺少匯率不可默認為 1

本批只修補 `BudgetManager._default_exchange_rate`：原幣與換算本幣不同、
未明確提供 exchange_rate 且既有預設表找不到該 pair 時，拒絕新增／修改，
回 ValueError 提示提供 exchange_rate。不能把不同幣別當成等值。

同幣別仍可使用 1；既有表內 pair 及顯式匯率沿用既有行為。
預設表不是本批驗證過的即時／歷史市場匯率；本批不更新其值或來源。
現有未知 pair 的交易仍可讀取；後續修改若缺匯率會先拒絕。
「未改幣別時保留原匯率」仍待 R05，不以本批偷偷補作。

沒有 migration、歷史回填、前端改動或正式資料操作。

### 驗收證據

- 基線：隔離 PostgreSQL 全套 475 passed。
- RED：新增／修改的兩個 regression 因未拋 ValueError 失敗，3 項成功契約通過。
- GREEN：新增 5 項通過，完整後端 480 passed。
- 檢查拒絕後即使 commit，交易、帳戶、分攤與 movement 都不變；
  同幣別、既有 USD 預設與顯式匯率則驗證持久化金額及帳戶扣款。
- GBP 僅是隔離 DB 的測試幣別，40 是合成測試匯率，不是正式匯率設定。
- 測試：`tests/test_exchange_rate_guard.py`；只使用本批 tmpfs PostgreSQL，
  另以連線 allowlist 與外網阻擋保護，未呼叫真實 LINE／Gemini。

### 剩餘範圍

R04 月報混幣與個人報表幣別語意尚未修補；R05 編輯保留匯率、R06 換算／分攤
尾差與 R07 歷史帳戶幣別保護仍依既定順序後續執行。S3 尚未完成，不能據此公開
接收真實財務資料。S1 staging、S2 正式併發／歷史帳務證據及其他發布門檻仍保留。
