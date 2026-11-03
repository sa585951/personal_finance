# 測試、問題修復與回歸狀態

更新日期：2026-11-03。保持 `codex/nomica-s3-fx-guard`，不 Push／Merge／建立 PR。
本文件是既定 S1～S6 的測試追蹤，不重排開發範圍。

最新本機驗收（2026-11-03）：完整後端 **640 passed**、零 skip；styles／lint／build／五尺寸深淺色 mock UI 重跑通過。獨立審查 2 項 Important 已各以 RED→GREEN 修補。
下方 489／506／514／520 等數字是各批歷史證據，不代表最新總數。

## 已證實與已修復

| ID | 證據與狀態 | 尚缺驗收 |
| --- | --- | --- |
| R01 | 已修補不安全旅行／月報查詢組合 | 正式查詢隔離與部署證據 |
| R02/U06 | 已改純文字／DOM value；惡意對話框 UI regression 已有紀錄 | 正式版本／實機回歸 |
| R12/R13/R14 | OAuth state／nonce、同源 Cookie 與公開設定修補已提交 | 真 LINE、正式代理、手機 PWA |
| R03 | S2 帳戶與交易鎖已提交；前輪 475 passed | 正式負載、多實例及歷史 reconciliation |
| R04 缺匯率 | 2de71ff；前輪新增／修改先 RED 後 GREEN，完整後端 480 passed | 與其餘 R04 月報問題分開追蹤 |

以上表格的 475／480 是前輪證據。本輪在新專用 DB 重跑完整 suite，結果為 489 passed（原 480 + 新增 9），包含 migration smoke tests。

## 待驗收與缺陷追蹤（各批歷史證據）

| ID | 現有依據 | 本輪結論 |
| --- | --- | --- |
| R04 月報混幣 | calculate_monthly_report_expenses 對 converted_amount／converted_share_amount 直接聚合，未分幣別 | 已用合成 DB 重現：TWD 600 + USD 20 得到無幣別總額 620；本機 Bug 已依確認規則修補：非 TWD 拒絕，17 項針對測試通過；不宣稱正式資料影響已盤點 |
| R05 編輯換匯 | 未提供 exchange_rate 會再取預設值 | 已重現並修補，8 項新案例及完整 suite 514 passed；未回填歷史資料 |
| R06 分攤尾差 | 現有分攤與換算流程需驗證守恆 | 已重現儲存四捨五入不守恆並按確認規則修補；6 項案例與完整 520 passed |
| R07 帳戶改幣別 | update_account 可直接更新 currency | 已依確認的建立後固定幣別規則修補；6 項針對測試及完整 526 passed |
| 預設匯率表 | 靜態 preset，沒有本輪市場來源／時效驗證 | 不把預設值稱作即時或歷史市場匯率 |
| data/*.json | 來源、真實性與保留需求未確認 | 不刪除、不推定為合成 fixture |

AI／LINE 互動維持停用；G-AI 的費用、Key／Billing、隱私與額度驗收仍未完成。

## 測試案例與結果

| 類型 | 案例 | 對應測試／狀態 |
| --- | --- | --- |
| 正常 | 同幣別不需跨幣報價；既有 pair／顯式匯率持久化正確 | 新增純函式案例 5 passed；既有 DB 案例本輪通過 |
| 異常 | 缺匯率拒絕新增／修改，commit 後四張帳務表不變 | test_exchange_rate_guard.py 本輪 5 項隨完整 suite 通過 |
| 邊界 | 兩幣別皆受支援，不代表 pair 有報價：KRW↔USD、KRW↔EUR | 新增 4 passed，拒絕默認 1 |
| 回歸 | 缺匯率不影響既有交易／餘額；發票／Transfer／LINE draft 不重複寫入 | 本輪完整 suite 489 passed；不是正式 API／實機驗收 |
| 待驗證 | 同月 TWD 日常與 USD base 的旅行 split 不可直接相加；同幣別、exclude、無本人 split、刪除交易需維持原契約 | 混幣診斷已重現；exclude／無本人 split／刪除交易的針對性修補驗收仍待下批 |

本輪已執行 `tests/test_exchange_rate_boundaries.py`：**9 passed**。
執行時禁止所有 DB 與網路連線、關閉 dotenv；未修改 production code。
另已取得使用者同意，在新專用 DB 執行完整後端回歸：489 passed，零 skip。
R04 混幣另外以臨時 diagnostic 重現（1 項診斷執行成功）；這表示成功觀察錯誤，
不是月報驗收通過，不計入 489 個 regression。前端／實機本輪未測。

## QA DB 使用邊界

使用者指定容器 `nomica-qa-20261020-a15822` 已唯讀確認為 running、PostgreSQL 16、
loopback port 55432，掛載同名持久化 volume；設定的既有 DB 為
`nomica_scenario_20261020_a15822_test`。沒有連線或檢視既有 scenario DB 內容。

使用者已明確同意沿用容器並另建空 DB。已新建並先驗空的
`nomica_s3_r04_review_20261030_test`；runner 僅允許此 DB，並禁止外網。
此 DB 供後續合成資料測試保留，沒有移除或覆寫既有 scenario DB。
不得直接對舊 DB 執行 drop_all；不得停止／刪除此共用 QA 容器或 volume。
最新執行授權：每批驗證通過可自主 commit；僅遇需求歧義、未授權真實／破壞性操作等停止條件時詢問。


## Migration 核對

本地 `alembic heads`：`20261021_0018 (head)`，接在 `20261020_0017`。
0018 是 S1 OAuth state 表；S2、R04 匯率 guard 與本輪測試補強均未新增 migration。
本輪 suite 含空 DB 與既有版本升級案例。這不證明既有 QA／正式 DB 已套用 head；
未讀取那些 DB 的 alembic_version，也未對它們執行 upgrade。

## 本批交付邊界

只新增邊界測試與此追蹤文件，未修改業務程式、schema 或既有測試行為。
R04 月報混幣的下一批修補需維持交易原幣／旅行結算幣別／個人報表幣別分離，
不能直接把既有 converted_share_amount 重新標成 TWD，也不能沿用錯誤總額 620
作正式 regression 預期值。已獲使用者授權，測試補強驗證通過可自主 commit。


## R04 已確認規則

使用者已明確決定：第一版只提供 TWD 報表，應納入的非 TWD 旅行分攤必須
明確報錯，保留原始資料、不靜默漏算。此規則供下一批 R04 RED→GREEN 使用；
本次測試盤點 commit 尚未包含實作，不能宣告月報已修復。

R04 修補批次：完整後端 506 passed，17 項新案例；詳見 `docs/s3-fx-correctness.md`。

## S3.4 R09 驗證結果

成員／split 唯一性與 15 人共享容量已修補，完整後端 536 passed。
新 head 為 20261030_0019；前文 0018 是該輪核對的歷史 head，不代表目前最新。
重複 preflight、含資料升級與 rejoin／外部成員回歸均已測；既有／正式資料未盤點。
S3.1 的 UI 小數與無效數值等剩餘驗收仍須核對，不以 R04～R09 完成直接宣告全 S3。

## S2.3 R16 補漏

R03 本機完成不代表 S2 全完成；已補回原計畫的請求結果隔離。
四個原始 regression 已修補，並保留 LINE 相容 helper 的真實事件驗證；
最終 8 項針對測試與完整後端 541 passed。已開放呼叫方不再讀共享 last_*。

## S3.1 收尾

小數原生輸入、finite／範圍／精度與換算尾差已補驗證；新增數值 34 項，
完整後端 575 passed。前端 check:styles／lint／build 與五尺寸深淺色 mock UI
通過。S3 後續仍不得取代正式資料影響、部署及實機驗收。


## S3 最終本機回歸與 S4 停止點

額外補上 pending 與跨使用者的月報控制案例，完整後端 **577 passed**（38.56s）。
R04 月報驗收共 19 個參數化案例；非 TWD 原幣已換成 TWD 可納入，exclude／pending／
無本人 split／已刪除／其他月份或使用者的異幣不會誤擋本人當月報表。
S2.3 R16 已補回；S3 的 R04～R07、R09 與 UI 小數／數值邊界已有本機證據。

進 S4.1 前需確認舊 key 相容規格：現有一般交易只有 client_request_id，未保存原始
payload 指紋；舊測試目前明確允許同 key 以不同金額回放原 ID。新請求須依原計畫
拒絕不同 payload；已被編輯且缺原始指紋的舊請求，不能假裝用現值就可還原原意。
使用者已確認：舊 key 無原始 payload 指紋時，一律回 409，附既有交易 ID；保留資料、不自動換 key 或再次寫入。新請求須保存原始指紋；相同 payload 正常回放。S4.1 實作／驗收仍待下一批，不跳過去改生命週期。

S4～S6、正式資料盤點／還原／部署、真 LINE／手機實機、平台／隱私／保留與完整匯出
仍未完成，不可宣告已達公開或正式發布門檻。

## S2／S3 獨立審查收尾（2026-11-03）

fresh-context reviewer 檢查 d5257ab..a7d7056，發現 2 項 Important，無 Critical／Minor。
已用專用合成 PostgreSQL 重現：舊 9 位 rate 分別入庫捨入後，只改標題誤扣 0.0001；
極大有限指數在 abs() 拋 Overflow，使新增／修改 amount、rate、share 回 500。
最小修補保留財務意圖未變時的既存換算額／split（含 ID），範圍比較改用 copy_abs()。
18 項新案例（14 regression 原先 RED、4 控制），完整 **595 passed（48.16s）**。
顯式金額／匯率／成員／分攤變更仍重算；未修補或回填歷史資料。無新增 migration，head 為 0019。

重建臨時 runner 後只允許 nomica_s3_r04_review_20261030_test 並阻擋外網。
恢復原 QA 容器，未停止／刪除容器或 volume，未讀寫舊 scenario DB。
審查未覆蓋的 account 累加溢位、其他 AssetManager 數值入口、生命週期併發、
匯率市場有效性、正式資料／DDL 耗時及 Provider／實機驗收繼續列為未驗證風險。

## S4.1 Backend 批次（2026-11-03）

原始請求指紋與 legacy 409 已實作；19 regression 先 RED，新增旅行上下文／排序
控制後共 22 項通過，完整後端 **617 passed（54.39s）**，零 skip。
覆蓋跨 session、編輯／刪除後原意回放、不同 payload、4 worker 並發一次、
失敗後 commit 仍零副作用、同 key 跨使用者，以及三種 legacy 狀態回 409／本人既有 ID。
沿用 0017 financial_commands，無新增 migration。
S4.1 Web 持久恢復、公開入口 key 驗收仍未完成；S4.2～S6 不跳過。

### S4.1 Backend 獨立審查與下一批驗收

Fresh reviewer 核對 3069422..1631a3e、22 個案例與全部 Review Focus，無具體
Critical／Important／Minor；task-done 再跑完整 **617 passed（51.85s）**。
此結論只支持 Backend 批次，不等同完整 S4.1、公開門檻或部署通過。

唯讀核對的後續 client 缺口（不是已完成）：

| 原 ID／入口 | 現況證據 | 下一批必要驗收 |
| --- | --- | --- |
| N04/U03 日常新增 | UniversalAddView 只保存 RAM clientRequestId，TransactionForm 直接 POST | 送出前 owner-scoped 保存原 payload/key；逾時／500／401／409 不換 key，重整仍可核對／重試；不同 payload 不重複扣款 |
| N04/U03 旅行新增 | TripsView.addTripExpense 沒帶 key | 每次新意圖帶 key；同筆連點／掉回應／重整只建立一次；trip 切換不能把舊 pending 套到另一旅行 |
| N04/U03 Transfer／Settlement | 已使用 pendingFinancialCommand sessionStorage | 保留既有流程，重整回放、400 可修改、409 不自動換 key 回歸 |
| N04/U03 LINE draft | 鎖草稿且以 draft UUID 提交 | 不呼叫 Provider 的合成確認回歸已隨617通過；真 LINE 尚未驗收 |
| N04/U03 QR resolve | 鎖 receipt，linked 狀態回放；建立走同一 TransactionService | 重掃／重送只扣一次的合成回歸已通過；不能把服務層通過當手機相機驗收 |
| N04/U03 公開相容性 | POST /api/transactions 仍 optional key | 同步 client 與必填／相容性切換驗收前，不宣告所有公開寫入具備冪等 |

使用者已確認舊 key 409 的解除規則：明確核對既有紀錄後，才清除本機 pending；既有交易不變，不自動換 key 或重送。此 client 批次已實作，見下方本輪結果。
S4.2 旅行生命週期與其他交錯寫入、S5 正式資料／還原／隱私、S6 仍依原序待辦。

## S4.1 client 批次（2026-11-03）

日常／旅行新增已接 owner/scope pending，保存原payload/key後才POST；reload原資料
重試、legacy ID及明確核對解除、錯誤狀態與儲存失敗保護已完成。
新增 test-transaction-recovery.cjs **25組** Chrome／mock API案例通過，含兩種入口的
正常、丟回應、400／401／409／500、legacy解除、owner切換、storage讀寫失敗，
reactive巢狀凍結、stale覆寫／late清除、auth400不得丟掉未知請求，以及5尺寸×深淺色
長字串／按鈕可操作性。已觀察原失敗再修補；完整UI、styles／lint／build通過。
完整後端617 passed（49.49s）；本批無Backend／schema變更。

實際整合另外通過：Chrome→localhost實際API→同一授權QA DB的獨立schema
`qa_s4_client_20261103_8ca3a33c`，不與public smoke schema共用資料表。
每日／旅行各201提交後丟回應，reload同key回200，只寫一次；legacy409核對解除
無額外POST。SQL獨立核對balance760=1000-40-100-100，三交易／三movement／
兩command，reconciliation 1 matched／0 mismatch。合成身份走實際Cookie/session，
不是Provider登入驗收。原scenario DB未讀寫，QA容器／volume保留；只停止本輪本機
Flask／Vite。臨時runner、cookie、synthetic evidence與截圖不進版控。

剩餘S4.1門檻：公開POST /api/transactions仍optional key，未宣告所有公開寫入皆
冪等。已提出是否改必填的相容性決策（舊client將回400），未核定前不切換。其他
財務建立入口／未持久化LINE相容流程仍按原計畫核對，不因兩個Web入口完成而
宣告S4～S6或G1/G-AI/G2。

### S4.1 client 審查修補（同輪 fix pass）

獨立審查發現旅行在 auth await 後才讀表單；真 Vue 延遲回應已重現 clicked100
卻 POST999／另一編輯交易7。改為驗證後、任何 await 前 JSON snapshot，重試仍用
原 pending；欄位／編輯模式後續變更不修改原提交。
另將 reviewer 未判定的 preflight→POST 換Cookie風險升為Important處理：新增可選
X-Nomica-Request-Owner 與真正認證actor比對（只拒絕，不授權），不符409
REQUEST_OWNER_CHANGED、零財務異動，client保留原pending並停止此帳號流程。
已更新兩個Web入口；省略header的舊client相容保留，不宣稱那些client也有此保護。

新增4組Chrome regression與3項API測試，先RED再GREEN；現在恢復案例29組，
完整Backend **620 passed（53.09s）**、完整UI／styles／lint／build通過。
實際HTTP再驗日常／旅行掉回應及legacy解除，另將A認證preflight後POST Cookie
改B，真正API回409，B零交易；獨立SQL仍760、3交易／3movement／2command、
reconciliation1 matched／0 mismatch。本輪獨立合成schema：`qa_s4_client_20261103_182068d1`。
原schema及前輪臨時證據保留；既有scenario DB／正式資料未碰。無新增migration。

使用者已核定公開交易POST必填key、部署前同步更新寫入client；接續Task3實作，
目前此commit仍optional。不是未決產品規格，不再重複詢問。

## S4.1 公開交易key門檻（Task3）

已依使用者核定改成必填UUID字串；missing/null/empty/非字串/invalid UUID400，
零交易／帳戶／split／movement／command寫入。18拒絕案例加internal與owner優先
控制，共20項通過。先RED10 failed／9 passed，最小HTTP guard後修補。
完整Backend639 passed（56.63s），新增優先控制另隨target20通過；最終task-done
總數另記。完整前端檢查與29組恢復／原UI通過。
原錯誤遮蔽、數值、parse event測試提供有效key繼續驗原目的，沒有用新400遮蓋舊錯誤。
無新增migration；internal無key相容仍存在且不保證冪等。
實際HTTP新缺key400、所有正常回放／legacy解除／owner race409及SQL對帳通過；
最後獨立schema：`qa_s4_client_20261103_de14ab0b`。

本機規則完成不等於舊client已更新、正式DB已升級或G1通過。其他已開放帳務入口
仍需依原N04/U03盤點：AccountForm沒有提交鎖／key，AssetManager.add_account
每次INSERT帳戶及anchor；adjustment API仍optional key，這些未在本批修復或宣告
可靠性完成。預算軟刪除後重設R08亦仍待原序驗證，不跳過進S4.2。

### Task3 最終驗證與獨立審查

Task-done 全套 **640 passed（60.02s），零skip**；其後唯讀SQL再次確認獨立
scenario schema仍760、3交易／3movement／2command、B零交易、recon匹配。
Fresh reviewer審查d75d0e8..a27dcc9，無Critical／Important／Minor；另以純AST
方法驗21種不合法JSON/key、owner409優先與合法key通過，沒有載入app或寫DB。
原Task1/2已各自審查／TDD修補，不因此宣告全生命週期與正式部署通過。

下一原N04入口的受控診斷：真Vue AccountForm單次double-click送兩個完全相同
POST /api/assets，皆無key。所有API攔截，**未寫DB**；確認的是重複送出Bug，
不冒稱已實測重複帳戶／anchor。程式上add_account每次INSERT的資料影響仍須
後續合成DB重現與驗收。調整API仍optional key，尚未完成原payload比對回歸。
已詢問新增帳戶／餘額校正是否同步採必填公開契約；本次交易API授權不擅自擴成
其他API行為變更。等相容性決策後接續，不跳過原序進S4.2。R08亦仍待驗證。

本輪commits：bb78f13（Web恢復／legacy核對）、d75d0e8（凍結點擊／POST actor綁定）、
a27dcc9（公開交易key必填）。沒有Push／Merge／PR或正式DB升級。
