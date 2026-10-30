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

R04 月報混幣已依下方確認的 TWD 限制修補；R05 編輯保留匯率、R06 換算／分攤
尾差與 R07 歷史帳戶幣別保護仍依既定順序後續執行。S3 尚未完成，不能據此公開
接收真實財務資料。S1 staging、S2 正式併發／歷史帳務證據及其他發布門檻仍保留。


## R04 第二批：TWD 個人報表限制

依使用者明確決定，含有應納入且 base_currency 非 TWD 的分攤／日常金額時，
個人報表明確拒絕，不重標幣別、不跳過支出，也不修改原始帳務。
聚合依幣別分組並驗證，避免查詢間新出現的異幣被直接混加；月報投影在分頁前
驗證整個已篩選範圍，讀取每列時再驗證。收支摘要的月份條件先下推至 DB。
API 的預期拒絕為 400；其餘未預期例外仍遮蔽細節，不因本批放寬所有 ValueError。

RED：4 個報表入口未拒絕；API 另有 6 個入口回一般 500。修補後新增 17 項
皆通過，完整後端 **506 passed**。Auth 為替身、帳務為專用合成 PostgreSQL，
未呼叫外部 API，不代表正式登入／部署／實機已驗收。

本輪沒有 migration，head 仍為 20261021_0018。R05／R06／R07 尚未完成。

## R05：編輯保留歷史匯率

原幣及本幣未變且沒有顯式新匯率時，使用交易原先保存的 rate。
修補前 6 個案例重現誤換匯／未知 pair 被拒絕；修補後 8 項全部通過，
完整後端 **514 passed**，reconciliation mismatch 0。涵蓋原幣省略／同值、
日常 USD／GBP、旅行 JPY 分攤、改金額、顯式新 rate 與換幣別。
沒有 migration 或歷史批次更新。R06／R07 仍待完成。

## R06：四位小數換算分攤守恆

已重現交易換算 0.0067／分攤合計 0.0066 的缺陷，也涵蓋分攤四捨五入造成超額。
按確認的最大餘數規則共用修補 equal／custom，原幣尾差規則不變。
4 項 regression 先 RED；最終 6 項含零分攤／無尾差邊界通過，完整後端
**520 passed**。成員集合、原幣合計、固定排序及 metadata edit 穩定性皆有驗證。
沒有 migration 或歷史回填。R07 帳戶幣別保護仍待處理。

### R04 前端錯誤狀態回歸

Chrome 先重現首頁將幣別原因蓋成網路錯誤、分析錯誤時仍有總額卡；最小修補後，
首頁保留 API 的幣別提示，分析在載入／錯誤時不顯示金額內容。
新增真實 Vue rendering／mock API 回歸；check:styles、lint、build、五尺寸深淺色
UI 皆通過。沒有加入導覽／換匯新功能；不是正式 API、相機或手機實機驗收。

## R07：歷史帳戶幣別保護

建立時即有含幣別的 opening anchor，依使用者確認規則，update_account 在任何
寫入之前拒絕異幣（保留既有帳戶鎖）。同幣別可更新名稱，跨使用者仍拒絕。
4 項 regression 先 RED；最終 6 項全部通過，完整後端 **526 passed**。
含零餘額、已有交易、刪除／歸零、同次名稱及 balance 拒絕零異動與 HTTP 400。
沒有 migration、歷史換幣或批次修正。R04～R07 已有本機驗證，S3.4 R09 仍待完成。

## S3.4 R09：唯一性與容量

5 項 regression 先重現重複身份／並行超限／外部成員未受限；migration 3 項先 RED。
補齊 trip/user、transaction/member unique constraints，兩個加入入口共用 trip 鎖，
active 上限 15；rejoin 沿用 member ID，NULL user 的同名外部旅伴可共存。
7 項成員／DB 案例、3 項新升級案例及原 migration smoke 通過；完整後端
**536 passed**。`20261030_0019` 接在 0018，只加約束，先檢查兩類重複；
若有重複就停止、保留舊 revision 與所有資料，禁止自動合併或刪除。

只在已授權的專用合成 DB 測試 0019。既有 scenario DB／正式 DB 未套用。
正式升級須先備份、暫停成員／分攤寫入並核對重複與資料量；發現異常先在隔離
副本列處置方案並取得批准。建立 unique 可能持鎖，正式耗時與升級仍未驗收。
舊初始 migration 的 moving metadata 問題未在本批重寫（R20 留待原計畫）。
