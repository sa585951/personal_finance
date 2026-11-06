# 文件入口與版控規則

更新：2026-10-30。判定現況時先看程式、測試及下列現行文件，不從舊 Phase 推定。

| 類型 | 文件 | 維護方式 |
| --- | --- | --- |
| 產品方向與階段 | `product-roadmap.md` | 唯一目前進度入口；保留原問題 ID |
| 財務／API 合約 | `finance-contract.md`、`api-contract.md` | 隨行為變更更新並版控 |
| 寫入／安全／部署 | `financial-write-safety.md`、`security-boundary-hardening.md`、`deployment-checklist.md`、`s2-ledger-concurrency.md` | 記錄本機與正式驗收差異並版控 |
| 目前功能規格 | `receipt-import-v1.md`、`visual-design-system.md`、`product-event-taxonomy.md`、`line-command-reference.md` | 隨功能維護；LINE 指令存在不代表入口已開放 |
| 領域與相容背景 | `asset-allocation-domain-plan.md`、`legacy-schema-inventory.md` | 保留依據，不以舊日期判定無用 |
| 已收尾研究 | `m2-pwa-alpha-plan.md` | 保留有限證據及未驗證假設，不重啟原招募關卡 |
| 舊情境案例 | `phase5-simulation-test-script.md` | 保留作案例庫；依現行合約改寫測試後才執行 |
| 歷史計畫 | `archive/` | 封存，不追著新版本更新；不作部署／安全指令 |

## 哪些資料需要版控

需要版控：維護中的程式、測試、migration、lockfile、無秘密的設定範例、現行合約、
決策與必要歷史依據。文件本身通常很小，封存仍留在 Git，利於追溯。

不需要版控：Python 快取、node_modules、dist、測試截圖／暫存報告、coverage、
本機工具權限設定、`.env`、Token、DB dump、真實財務資料及個資研究原始紀錄。
`.gitignore` 不會自動移除已追蹤檔案，也不會抹除 Git 歷史。

.gitignore 已補齊本機／產物排除。本次停止追蹤已提交的 `.pyc` 與 `.claude/settings.local.json`，保留本機檔案。
沒有改寫 Git 歷史或宣告歷史完全無秘密；若發現已洩漏憑證，另做撤銷／輪替。

`data/*.json` 仍被歷史 `config.py` 命名引用，但 active PostgreSQL 路徑未直接引用
這些常數。本次未檢視或刪除其內容；目前資料不足以判斷是否為純測試資料。
暫保留現狀，待確認來源、備份與相容需求後，才決定改為合成 fixture、移出版控
或另處理歷史敏感資料。不要只加 ignore 後就聲稱已清除。
