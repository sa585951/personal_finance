# 文件入口與版控規則

更新：2026-11-09。判定現況時以程式、migration 與測試為準，其次是下列文件。

| 類型 | 文件 | 用途 |
| --- | --- | --- |
| 目前進度 | [current-progress.md](current-progress.md) | 已完成、待驗收與下一步 |
| 產品方向 | [product-roadmap.md](product-roadmap.md) | Milestone、平台分工與收費假設 |
| 財務與 API 合約 | [finance-contract.md](finance-contract.md)、[api-contract.md](api-contract.md) | 隨行為變更更新 |
| 寫入安全 | [financial-write-safety.md](financial-write-safety.md)、[s2-ledger-concurrency.md](s2-ledger-concurrency.md)、[s3-fx-correctness.md](s3-fx-correctness.md) | 冪等、併發、匯率與數值規則 |
| 安全與部署 | [security-boundary-hardening.md](security-boundary-hardening.md)、[deployment-checklist.md](deployment-checklist.md) | 正式設定、部署步驟、封閉測試營運與試用者上手說明 |
| QA 台帳 | [test-fix-status.md](test-fix-status.md) | 缺陷 ID、修補與證據；舊批次計畫已併入 |
| 功能規格 | [line-ai-pilot.md](line-ai-pilot.md)、[receipt-import-v1.md](receipt-import-v1.md)、[visual-design-system.md](visual-design-system.md)、[product-event-taxonomy.md](product-event-taxonomy.md) | 功能行為與驗收 |
| 領域背景 | [asset-allocation-domain-plan.md](asset-allocation-domain-plan.md)、[legacy-schema-inventory.md](legacy-schema-inventory.md) | 資產配置設計依據；舊表移除前的相容紀錄 |

各平台入口：[根 README](../readme.md)、[frontend/README.md](../frontend/README.md)、[ios/Nomica/README.md](../ios/Nomica/README.md)。

## 哪些資料需要版控

需要版控：程式、測試、migration、lockfile、無秘密的設定範例、現行合約與規格。

不版控：已結束的批次計畫與封存文件（需要時從 Git 歷史查）、Python 快取、`node_modules`、`dist`、測試截圖、coverage、本機工具設定、`.env`、Token、DB dump、真實財務資料與個資研究紀錄。

規則：
- 文件過時就刪除，不另建封存資料夾；Git 歷史保留原文。
- 刪除或改寫文件時，同步修正其他文件中的連結。
- `.gitignore` 不會移除已追蹤的檔案，也不會抹除 Git 歷史；若發現憑證外洩，另行撤銷與輪替。

`data/*.json` 仍被舊 `config.py` 命名引用，現行 PostgreSQL 路徑沒有讀取。確認來源與備份前維持現狀。
