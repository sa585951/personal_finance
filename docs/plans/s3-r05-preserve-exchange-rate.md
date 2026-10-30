# S3 R05：編輯保留歷史匯率

Spec：已確認 R05，僅改標題等非金額欄位時，原匯率、換算額及帳戶淨影響不變。
交易幣別與換算本幣不變且未傳新 rate 時保留原 rate；顯式新 rate 或改幣別沿既有契約。
Constraints：不改 R04／報表限制、歷史回填、schema、前端或匯率表；只測專用 DB。

## Task 1: 編輯時不重新套用預設匯率

Interfaces：update_transaction 的 rate → 帳戶 reversal/apply、transaction、trip splits。

1. 真實 DB 測試 USD 非預設 rate 與 GBP 無預設 pair 的 metadata edit；原幣省略及相同原幣都驗證。
   Expected: RED，現碼重新套預設或拋缺 rate。
2. 旅行分攤 metadata edit、改金額仍保留 rate；明確新 rate、換幣別仍按明確意圖計算。
   Expected: 無意改匯率之案例 RED；既有明確意圖成功。
3. 最小修補 update rate 選擇，保持其他欄位／驗證不變。
   Expected: 新案例 GREEN，reconciliation mismatch 0。
4. `python3 /private/tmp/nomica-s3-r04-review-20261030/run.py tests -q`。
   Expected: 全套通過，零 skip，記錄實際數量。
5. 更新 R05 狀態並 commit；用相同全套命令 task-done。

Review Focus：只在原幣與本幣均未變時保留 rate；顯式新 rate 不得被忽略；未知 pair 不得再拒絕單純 metadata edit；旅行 split 與帳戶保持一致。
