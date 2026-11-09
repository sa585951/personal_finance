# Nomica 目前進度

快照：2026-11-10，分支 `codex/beta-readiness`（基於 main `bac4c14`）。長期方向見 [product-roadmap.md](product-roadmap.md)。

## 已在 main（已部署）

- P0：CI（後端全量、前端、端對端）、帳戶預設上次使用、匯出／刪除帳號／登出所有裝置
- Web 帳簿式改版（今天、記一筆、明細、我的）、Web 一句話記帳（本機規則）
- LINE：一句話記帳、Gemini（同意、月上限預設 5 USD）、帳戶選擇依使用頻率排序並可翻頁與打字選擇
- 正式資料庫已升級到 `20261109_0020`

## 這個分支（封閉測試前準備）

| Commit | 內容 |
| --- | --- |
| `8a09570` | LINE AI 每人每日上限（預設 30 次）與 80% 用量 LINE 通知；migration `20261110_0021` |
| `aab8f54` | 刪除帳號 30 天後永久清除（`scripts/purge_deleted_users`）；隱私權政策與服務條款頁 |
| `85d7616` | 旅行列表改為列表；旅行詳情以支出為主、浮動「記一筆旅行支出」、設定分頁、旅行支出預設帳戶 |
| `a5ebec3` | 帳戶、預算、分析頁整理；移除信用卡誤報與錯誤的旅行數；預算用詞一致 |
| `6ab45d3` | 今天頁：每日可花、預算引導、情境卡（旅行中／信用卡繳款）；量測事件與 `scripts/beta_metrics`；migration `20261110_0022` |
| `abdeaa2` 與本次 | 封閉測試營運與試用者上手說明（併入 [deployment-checklist.md](deployment-checklist.md)） |

本機結果：後端 774 passed（含 PostgreSQL）；端對端、mock UI、lint、check-styles、build 通過。

## 開始封閉測試前

依 [deployment-checklist.md](deployment-checklist.md)「封閉測試 → 開始前」逐項完成：備份 → migration 到 `20261110_0022` → 部署 → 環境變數 → 清除排程 → 填政策頁與上手說明的營運者與聯絡方式 → 實機驗收。

## 尚未完成

- Web 一句話記帳接 Gemini 與共用額度（排在測試第 1～2 週）
- 帳戶、預算、分析的完整重排；桌面表格；PWA 圖示與 LINE 頭像
- 隱私權政策與服務條款的法務審閱
- 舊 LINE 程式（約 6,900 行）移除、大檔拆分、OpenAPI、監控擴充
