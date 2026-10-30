# S3.1 U02／R06：已核定小數的表單驗收
Spec：原 S3.1 UI 可輸入核定小數；現行 USD／EUR 兩位，TWD／JPY／KRW 整數。
只修原生日常／旅行金額與自訂分攤輸入限制，不改格式、匯率或新功能。
## Task 1: 表單允許正確幣別精度
1. 真實 Vue／Chrome checkValidity，日常 USD 1.23、0.01；旅行及自訂分攤 USD 同樣可輸入。
   Expected: 現況 step=1／min=1 阻擋，RED。
2. 依原幣設定 step，交易最小值依 step、自訂 share 仍可為0。
   Expected: USD／EUR 兩位可輸入、超精度／負數／整數幣別小數仍拒絕。
3. check:styles、lint、build、全 mock test:ui 通過後更新狀態並 commit；同 UI command task-done。
Review Focus：step/min 隨原幣切換；自訂零分攤合法；只改瀏覽器限制，不放寬後端精度。
