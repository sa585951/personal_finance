# 封閉測試營運手冊

四週封閉測試期間的部署、監控、停用與回退步驟。一般部署細節見 [deployment-checklist.md](deployment-checklist.md)。

## 開始前（一次）

| 項目 | 怎麼做 | 完成 |
| --- | --- | --- |
| 資料庫備份 | Supabase：確認自動備份已開啟，並在升級前手動建立一次備份 | [ ] |
| Migration | `DATABASE_URL='…' alembic current` 確認版本，再 `alembic upgrade head`，結果應為 `20261110_0022 (head)` | [ ] |
| 部署 | Render 部署對應的 main；Vercel 前端同步 | [ ] |
| 環境變數 | `GEMINI_API_KEY`、`NOMICA_LINE_AI_PAID_PROJECT_VERIFIED=true`；建議設 `NOMICA_ADMIN_LINE_USER_ID`（80% 用量通知）；`NOMICA_LINE_AI_DAILY_PER_USER` 不設即每人每日 30 次 | [ ] |
| 清除排程 | 每天執行 `python -m scripts.purge_deleted_users --apply`（例如 Render Cron Job，使用同一組 `DATABASE_URL`） | [ ] |
| 政策頁 | `frontend/src/constants/policies.js` 的營運者與聯絡方式改為實際內容 | [ ] |
| 上手說明 | 填好 [beta-tester-guide.md](beta-tester-guide.md) 的 `〔〕` 後寄給試用者 | [ ] |
| 實機驗收 | 見下方清單 | [ ] |

## 實機驗收

用兩個 LINE 帳號（A、B）：

- [ ] A、B 各自用 LINE 登入 Web，首頁看到的是各自的帳本
- [ ] Web：一句話「午餐 120」填入後記下，餘額正確
- [ ] LINE：「午餐 120」→ 選帳戶（翻頁、打字選擇各一次）→ 確認，只入帳一次
- [ ] LINE：規則看不懂的句子 → 出現同意說明 →「同意 AI」→ 重傳 → 草稿 → 確認
- [ ] LINE：「撤回 AI」後，同一類句子不再送 AI
- [ ] A 建立旅行並邀請 B；B 加入後兩人都能看到同一筆旅行支出，分帳結果一致
- [ ] iPhone 與 Android：掃描發票 QR、圖片備援、同一張發票重掃不重複記帳
- [ ] 「我的 → 帳號與隱私」：匯出資料可開啟

## 每週例行

```bash
DATABASE_URL='…' python -m scripts.beta_metrics --weeks 4
```

看四件事：

1. `people_with_2plus_days`：每週記帳至少兩天的人數
2. `web_sentence_unchanged_ratio` 與 `line_drafts`：一句話記帳是否準確
3. `new_people_via_trip_invite`：旅行邀請帶來的新使用者
4. `line_ai_usd_this_month`：AI 費用

同時整理本週回報的問題，標記為「帳務錯誤」「看不懂」「想要的功能」。帳務錯誤當天處理。

## 出問題時

| 狀況 | 立即處理 |
| --- | --- |
| LINE AI 回覆異常或費用異常 | 停用 AI：在資料庫執行 `UPDATE line_ai_control SET enabled = false WHERE id = 1;`（立即生效，改回 `true` 恢復）。或把 `NOMICA_LINE_AI_MONTHLY_USD` 設為 `0` 後重新部署。規則記帳不受影響 |
| LINE 回覆整體異常 | 設 `NOMICA_LINE_MODE=disabled` 後重新部署，LINE 停止回應，Web 不受影響 |
| 新版本有問題 | Render 回退到上一個部署；Vercel 回退到上一個 Production 部署。本批 migration（0021、0022）只新增欄位與資料表，回退程式時不需降版資料庫 |
| 帳戶餘額看起來不對 | 唯讀檢查：`python -m scripts.reconcile_accounts --fail-on-issues`；不要直接改資料庫餘額 |
| 試用者要刪除資料 | 請本人在「我的 → 帳號與隱私」刪除帳號；30 天後由清除排程永久刪除 |
| 資料毀損 | 從 Supabase 備份還原到新資料庫、核對後再切換；清除排程刪掉的資料只能從備份找回 |

## 結束時

- 匯出最後一次 `beta_metrics`，整理訪談與回報。
- 決定 Web Gemini、iOS 與收費的下一步（見 [product-roadmap.md](product-roadmap.md)）。
