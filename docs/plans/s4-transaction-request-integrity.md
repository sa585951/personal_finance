# S4.1 N04/U03：一般／旅行交易請求完整性

> 使用已確認的 executing-plans，沿既定 S4.1 分批執行，不新增產品功能。

Goal：同 key／同原始意圖回原結果；不同意圖或舊 key 無法驗證回 409，未知結果不換 key。
Architecture：沿用 0017 financial_commands 與 IdempotencyManager，transaction.create operation 原子保存 fingerprint／原結果，不新增 Backend 架構或歷史回填。
Spec：docs/financial-write-safety.md、docs/api-contract.md；使用者已確認 legacy 無指紋回 409 並附既有交易 ID、保留資料。
Constraints：保留 Worktree／branch；不 Push／Merge／PR，不用真實資料；專用合成 DB、外網阻擋。AI／LINE 公開開關不改。既有 internal optional key 相容保留；公開入口必填切換須同步 client 並記錄部署門檻。

## Task 1: 交易 Backend 原始 payload 指紋與 legacy 409

Interfaces：BudgetManager.add_transaction → financial_commands、transactions／split／movement → TransactionService → POST /api/transactions。

1. 新增真實 DB／API 測試：新 key 同資料跨 session 回放、編輯後按原意回放、不同金額／帳戶／旅行／分攤拒絕、同 key 併發一次、舊 key 缺指紋（含編輯／刪除）409 附原 ID、跨使用者隔離、中途失敗 key 與帳務一起 rollback 後可重試。
   Expected: 現碼至少不同 payload／legacy 回放錯誤，先 RED；控制情境維持。
2. 使用 transaction.create 及明確 canonical payload（Decimal／UUID／日期標準化，缺省意圖凍結，分攤順序不改意義），沿既有 manager 私有寫入方法保存結果。舊 key 不從目前交易內容猜原 payload，不自動產生 key。
   Expected: RED→GREEN；同 key 衝突 API 409，legacy 回傳 owner-scoped ID，無持久副作用。
3. 更新舊 smoke「不同資料仍回放」預期為拒絕，保留原同 key 與跨使用者正常案例；完整 tests -q。
   Expected: 全套通過、零 skip；LINE／QR／Transfer／Settlement 回歸不得破壞。
4. 更新契約／進度，git diff --check、commit、task-done 全套驗證。
   Expected: verified bounded commit，S4.1 client 的未知結果恢復尚不宣告完成。

Review Focus：原始請求指紋不依賴編輯後資料；未提供 rate／currency 的重試不受後來 preset 或 trip 預設變化；無原指紋 legacy 拒絕必須回既有 ID；相同 key 多 worker callback 原子且失敗不保留 reservation；一般／旅行／LINE draft／QR 共用 manager，optional internal 無 key 不冒稱冪等。以上失敗模式均列 Task 1 測試。

## 後續既定 S4.1 批次（本文件不將其標為已完成）

- Web 日常與旅行提交保存原 key／payload，未知提交後重整以原資料重試，沿用 pendingFinancialCommand，補原生表單／錯誤回歸與獨立 API／DB 驗證。
- 核對公開 financial create 入口與相容性切換，不以局部交易修補宣告全部完成。
- Transfer／Settlement／LINE draft／QR 現有保護回歸，真 Provider 仍不開放或呼叫。

## Task 2: Web 日常／旅行未知提交恢復與人工核對解除

Spec supplement：使用者已確認，legacy 409 顯示既有 ID、保留原 key，只有明確「我已核對既有紀錄」才清除本機 pending；不修改／重送既有交易，不自動產生新 key。
Interfaces：pendingFinancialCommand 的 owner/scope storage → UniversalAddView／TripsView → 既有交易 POST；成功或確定400清除，401／409／500／網路未知保留。公開必填 key 切換仍獨立追蹤，這批不改 Backend 相容行為。

1. 新增 Chrome 真實 Vue／mock API 行為案例：daily/trip 保存原 payload/key、提交後掉回應、reload 原 key 重試、正常成功、400可修改、401/500/409不換key、legacy ID及明確解除零寫入、跨owner/scope隔離、storage失敗不POST、旅行巢狀reactive payload可保存且不被後續變更污染。
   Expected: 現碼無恢復／旅行無key／reactive structuredClone失敗，先RED；不使用source文字斷言。
2. 最小共用 PendingTransactionRecovery 顯示凍結原資料／重試／legacy核對解除。daily與trip沿用openPendingCommand；不可因切換模式、返回、reload或trip切換自動換key。legacy只在確認409+ID後允許明確解除；reload可重試原請求以取得409，不猜測ID。
   Expected: 新案例GREEN；401/409不自動再送，清除pending不POST、不改帳務。
3. 對前端跑styles/lint/build、完整UI；專用DB runner完整Backend。
   Expected: 全部通過，與真實後端／DB整合證據分開。
4. 執行localhost Chrome→Flask API→已授權專用合成DB：daily/trip提交後丟回應、reload再送，API與DB獨立核對每個意圖只有一筆／餘額只扣一次；真Auth/Provider以替身隔離，不呼叫外網。
   Expected: 實際整合通過，否則明確記錄阻塞，不冒稱完成。
5. 更新契約／進度、git diff --check，commit、task-done；本批完成後fresh review，保留branch/worktree、不Push/Merge/PR。
   Expected: verified bounded commit。

Review Focus Task2：同一分頁owner與trip隔離；初始化storage失敗須fail closed；舊回應不得清除新scope的pending；400與未知失敗不同處理；legacy解除只清本機且必須明確核對；Vue reactive巢狀資料凍結；成功後清除不因刷新失敗再送。每項以可見狀態與實際送出payload驗證。

## Task 3: 公開交易POST必填key相容切換

Spec supplement：使用者已核定 POST /api/transactions 必填 client_request_id，缺少回400且零寫入，部署前同步更新寫入client；internal manager無key呼叫保留。expected-owner不符仍先409保護原帳號意圖。
Interfaces：已更新Web daily/trip request → authenticated POST guard → 共用TransactionService/Manager；QR/LINE內部由既有伺服器key保護，iOS目前唯讀。

1. 新增實際合成DB／Flask API的missing/null/empty/非字串/invalid UUID拒絕矩陣，日常／旅行各驗證commit後零財務副作用；internal無key正常控制。
   Expected: 現碼missing key仍201、object/list可能500，先RED；internal控制維持成功。
2. 最小HTTP guard要求非空字串key，再沿既有UUID驗證；不改internal/schema，也不開放AI/LINE。
   Expected: 全矩陣400／零異動，正常同key回放不變。
3. 完整Backend回歸；既有route failure／numeric測試補入有效key以維持原測試目的，不以缺key400冒充原錯誤驗收。
   Expected: 全通過、零skip；缺key測試仍保留獨立覆蓋。
4. 現有完整UI／styles/lint/build，實際localhost API/DB確認缺key400與正常Web掉回應重整回放、legacy解除及owner綁定回歸。
   Expected: 兩種Web入口均帶key；不將local切換稱正式部署已完成。
5. 更新契約、部署前置與追蹤，commit／task-done，fresh final review。
   Expected: verified bounded commit，保留branch/worktree，不Push/Merge/PR。

Review Focus Task3：key guard不能被array/object輸入繞過變500；零寫入包含command reservation；internal無key相容仍存在；舊client未更新須明確400而非自動產生key；owner mismatch409不得被missingkey400誤清；所有既有異常測試仍驗證原意圖。
