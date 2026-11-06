# S3 R07：帳戶建立後幣別固定
Spec：使用者明確確認所有帳戶建立後幣別固定，包含零餘額；填錯另建帳戶。
不得更新錨點／movement／歷史交易來換標籤，同幣別及其他合法欄位仍可修改。
## Task 1: 拒絕直接更改帳戶幣別
1. DB regression：零帳務、帶交易、已刪交易／已歸零帳戶的換幣均拒絕，含同次名稱／balance 修改須零異動。
   Expected: RED，現碼接受且改標籤。
2. 最小修補 update_account，在任何 DB write 前驗證；既有 row lock 保留。
   Expected: GREEN，同幣別及跨使用者驗證不退化。
3. HTTP 回 400 清楚提示另建帳戶；真實 manager／DB、Auth 替身。
   Expected: 無資料異動；不連外部服務。
4. 專用 runner 全套 `tests -q`，通過後更新合約／進度並 commit，再 task-done。
Review Focus：拒絕要發生在名稱／餘額／billing 等寫入之前；零餘額也不能改；錨點與歷史保持不變；UI 傳同幣別不得誤擋。
