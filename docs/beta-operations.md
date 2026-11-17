# 封閉測試營運手冊（免費方案）

目前 Render、Vercel、Supabase 都是免費方案。以下規則依各平台過去的免費方案限制整理，**請以官方現行方案頁面為準**。

## 1. 讓 Render 保持清醒（LINE 不會等不到回覆）

Render 免費服務閒置約 15 分鐘會休眠，下次請求要等 30～60 秒。LINE 使用者傳句子時可能以為壞了。

1. 到 UptimeRobot（免費）新增一個 HTTP(s) 監控。
2. 網址填後端的 `/healthcheck`，例如 `https://<你的後端網域>/healthcheck`。
3. 檢查間隔設 5 分鐘。
4. 開啟「失敗時 Email 通知」，收件用 `kwcstudio.dev@gmail.com`。

注意：Render 免費方案每月有固定的免費運行時數，單一服務 24 小時開著大致用得完，請在 Render 後台確認用量。

## 2. 每週備份資料庫

Supabase 免費方案沒有自動備份。在主要的資料變動（migration、邀請新一批人）前，以及測試期間每週一次：

```bash
DATABASE_URL='<正式資料庫連線字串>' scripts/backup_db.sh
```

- 需要 `pg_dump`：macOS 可用 `brew install libpq`，並確保版本不低於 Supabase 的 PostgreSQL 版本。
- 備份檔放在 `~/nomica-backups`，含所有人的資料，只留在自己的電腦，不要上傳或分享。
- 每次備份後用 `pg_restore --list <檔案> | head` 確認有列出資料表。
- 測試期結束或不再需要的舊備份請刪除（隱私政策說明刪除後 30 天永久移除，備份不應該長期保留超過這個期限）。

## 3. 確認 AI 是關閉的

在 Render 環境變數確認：

- 沒有 `NOMICA_LINE_AI_PAID_PROJECT_VERIFIED`（或不是 `true`）。
- 建議一併移除 `GEMINI_API_KEY`。

確認方式：登入網頁後「我的 → 帳號與隱私」不應出現「AI 解析」區塊；在 LINE 傳一句規則看不懂的話，應該回覆「AI 解析目前暫停」。

## 4. 每週看什麼

- 「我的 → 使用概況」：誰在用、最後記帳時間。
- 「待改善的句子」：規則看不懂的句子，用來擴充規則。
- 回饋表單的回覆。
- UptimeRobot 是否有掉線紀錄。
