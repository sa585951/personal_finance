# S3 R06：換算分攤守恆

Spec：使用者已確認保留四位小數儲存，換算尾差只分給既有分攤者，按小數餘數
由大到小，同餘數以固定成員 ID 排序。原幣均分尾差規則不變。
Constraints：不改歷史資料、幣別、schema、匯率表或原幣分攤；不得替付款人新增分攤。

## Task 1: 使儲存後換算分攤合計等於交易換算額

Interfaces：add_equal_splits／add_custom_splits → Numeric(18,4)；新增與更新共用。
1. 真實 DB 測試 equal、custom（付款人無 share）、向上／向下尾差、輸入順序／編輯穩定。
   Expected: 現有逐筆 DB 四捨五入不守恆或排序不同的案例 RED。
2. 以原幣總額乘 rate 的四位 ROUND_HALF_UP 為目標；每筆先向下到四位，再依確認規則分配最小單位。
   Expected: 原幣不變，換算合計守恆、非負、零 share 不增加，成員集合不變。
3. 新案例及 `python3 /private/tmp/nomica-s3-r04-review-20261030/run.py tests -q`。
   Expected: 全套通過，零 skip，記錄實際數量；只用專用 DB。
4. 更新合約／狀態並 commit；同全套命令 task-done。
Review Focus：不依 input order；不給未分攤付款人加負擔；正／負的舊舍入差都修正；原幣守恆；沒有歷史回填。
