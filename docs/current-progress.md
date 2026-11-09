# Nomica 目前進度

快照：2026-11-09，分支 `codex/line-shortcut-pilot`。長期方向見 [product-roadmap.md](product-roadmap.md)。

## 這個分支包含的改動

| Commit | 內容 | 驗證 |
| --- | --- | --- |
| `1569661`、`72fe7e4` | LINE 一句話記帳草稿，預設啟用；確認前不入帳 | 本機與替身 |
| `dbe631c` | LINE Gemini：使用者同意與撤回、月費用上限、限流、即時停用；migration `20261109_0020` | 本機與替身 |
| `511cb0a` | LINE AI 月上限預設 5 USD；仍需付費專案確認 | 單元測試 |
| `4cd4b4c` | 修正 dev bypass 下 Web 寫入一律失敗 | 單元與端對端 |
| `9b06d69` | 新增收支預設上次用過的帳戶 | 端對端 |
| `73025a8` | 匯出資料、登出所有裝置、刪除帳號 | PostgreSQL 與端對端 |
| `a6539cb` | Web 一句話記帳（本機規則，不呼叫模型） | 單元與端對端 |
| `572937b` | Web 改版：今天、記一筆、明細、我的；黑白灰配色 | mock UI（5 尺寸、深淺色）、對比檢查、端對端 |
| `94be605` | GitHub Actions CI：後端全量、前端檢查、端對端 | 待第一次在 PR 上執行 |

本機最新結果：後端 751 passed（含 PostgreSQL smoke）；端對端、mock UI、lint、check-styles、build 通過。

## 部署前

1. 核對 Render 監聽的分支與正式 DB 的 migration revision，先備份。
2. 套用 migration 至 `20261109_0020`；若 `0019` 尚未套用，依 [deployment-checklist.md](deployment-checklist.md) 先核對重複資料。
3. 環境變數：可移除 `NOMICA_LINE_HELP_USER_IDS`（已不讀取）；`NOMICA_LINE_MODE` 可不設（預設記帳模式）。啟用 LINE AI 需 `GEMINI_API_KEY` 與 `NOMICA_LINE_AI_PAID_PROJECT_VERIFIED=true`。
4. 部署後確認：LINE 登入、Web 記一筆、LINE 規則記帳與 AI 同意流程。

## 尚未完成

- 刪除帳號後 30 天的永久清除排程。
- Web 一句話記帳接上 Gemini（共用 AI gateway 與同意，P1-10／P1-11）。
- 旅行、帳戶、預算、分析頁的版面重排；桌面表格版面。
- PWA 圖示與 LINE 頭像仍為舊藍色標誌。
- 舊 LINE 流程程式（約 6,900 行，只在本機 synthetic 模式可達）尚未移除。

## 下一步

1. 部署並以 5～10 位會一起旅行的使用者進行四週封閉 Beta。
2. 量測每週記帳天數、一句話記帳成功率、旅行帳本帶來的新使用者與付費意願點擊率。
3. 依結果決定 Gemini 共用解析、旅行口語記帳（M7）與 iOS（M6）的先後。
