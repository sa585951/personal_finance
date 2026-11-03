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
