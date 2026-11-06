# S2：R03 帳務併發與餘額正確性

更新：2026-10-30。前置：S1 本機修補基線；正式發布仍受 S1 staging 與 G1 限制。

## 已實作

- 一般收支先 `SELECT FOR UPDATE` 鎖住帳戶，再讀取最新餘額、驗證不足及寫入 movement。
  不再使用未鎖定快照覆寫；Web、發票 resolve、LINE 確認所共用的 BudgetManager 同步受保護。
- 編輯／刪除先鎖原交易，避免兩次依同一舊版本反轉；第二次刪除拒絕且零反轉。
- 跨帳戶編輯先依標準化 UUID 固定順序鎖住所有涉及帳戶，與 Transfer 保持相同順序。
  同帳戶反轉後重新讀取餘額，不重用反轉前的快照。
- 相對餘額校正、帳戶修改與刪除也先鎖帳戶；既有絕對校正、Transfer、私人 settlement
  posting 原本已有帳戶鎖，保留既有實作。絕對校正是設為指定值，不是 delta。
- 未更改金額、匯率、月報算法、交易 client key 契約或歷史資料，不新增 migration。

鎖保留到呼叫者 transaction commit／rollback；方法成功不代表已提交。
HTTP 未知結果的重試仍依既有 client_request_id 規則，鎖不等於冪等或網路可靠性。
資料庫 deadlock／timeout 應 rollback 並回一般錯誤，不能私自以新 key 重送。

## 驗收與測試

`tests/test_transaction_concurrency.py` 使用真正 PostgreSQL、獨立 Session 與同步起跑：

1. 四筆不同 key 的支出全部建立，餘額與 movement 全部保留。
2. 一般交易與 Transfer 共用帳戶，兩者正確反映。
3. 同筆交易雙編輯、雙刪除、編輯與刪除競爭，按最新版本反轉。
4. 兩筆交易相反方向換帳戶，不因鎖順序產生 deadlock。
5. 兩筆各自可負擔、合計不可負擔的支出，僅一筆成功。
6. 寫入餘額／movement 後故障，完整 rollback，後續提交仍可成功。
7. 相對校正與支出並行，兩個 delta 都保留。
8. 不同發票與手動收支並行，同帳戶全部反映，不依發票身分錯誤去重。

所有結果另驗證 Reconciliation mismatch 為零。既有 suite 同時涵蓋發票相同身分去重、
LINE 確認、Transfer 重播、settlement、migration 及 API 錯誤回滾。

本輪完整後端回歸：475 passed。測試使用專用 `nomica-s2-20261030` tmpfs
容器、空的 `nomica_s2_test` 與 Python 連線 allowlist；不使用既有 5432／5433 DB，
未執行正式 DB 測試。臨時憑證／runner／log 不進版控。

重跑需自行新建隔離空 PostgreSQL，確認 `DATABASE_URL` 與 `TEST_DATABASE_URL`
均指向它，關閉 dotenv 與外部 Provider，再設定 `RUN_DB_SMOKE_TESTS=1` 執行
`.venv/bin/python -m pytest tests -q`。測試會重建 schema，禁止指向正式／日常開發資料。

## 尚未宣告通過

本輪是本機 S2 核心 R03 修補，不是正式吞吐量、長時間壓力、多實例部署驗收或歷史
帳務已無損壞的證明。沒有自動修改既有不平帳資料；正式 reconciliation 需備份與
唯讀盤點證據後另排處置。一般交易相同 key 不同 payload 的完整衝突契約仍屬後續
重試治理，不藉本批鎖定宣告完成。S3 接續 R04／R05／R06／R07 幣別、匯率、
四捨五入與歷史語意；S4／S5／S6 及 G-AI 不因此跳過。

## S2.3 R16：請求結果隔離

原 S2 僅完成 R03，後續核對原計畫補回 R16。4 個 regression 重現共用 Manager
的 ID／replayed 串錯與非交易 endpoint 回 stale ID。
`TransactionCreationResult` 保留舊兩值 unpack，附 request-local transaction_id／replayed；
TransactionService 直接使用結果，Web／LINE／發票不再讀共享 last_*。
last_* 只保留內部舊測試相容，不是 request-safe API，新增呼叫方不得依賴。
帳戶／預算不建立交易，回 transaction_id=null 且不確認舊 parse event。
LINE 相容 helper 保留，但只接受呼叫方明確傳入的 creation_result，未提供不確認。

完整回歸曾發現刪除舊 helper 造成 3 項失敗，已恢復接口並以真實 DB 事件狀態
驗證 explicit／query／missing／stale 四種情況；不是刪除舊測試掩蓋失敗。
最終 8 項針對測試及完整後端 **541 passed**，零 skip。Auth／Provider 維持替身，
沒有開啟 AI／LINE 互動或新增 migration。原有 payload 冪等衝突仍接 S4，不混為結果隔離。
