# R04 回歸收尾：拒絕報表後不顯示誤導資訊
Spec：已確認非 TWD 報表要明確報錯、不顯示錯誤總額。只修既有錯誤狀態，不新增功能。
## Task 1: 保留首頁幣別提示、分析拒絕時隱藏總額
1. 用本機 Chrome、全 API mock 驗證首頁顯示 REPORT_CURRENCY_UNSUPPORTED 提示，分析錯誤時無總額卡。
   Expected: 現況兩項驗收不符，RED。
2. 最小修改首頁錯誤來源與分析既有內容顯示條件。
   Expected: 新案例與五尺寸／深淺色 UI regression GREEN。
3. check:styles、lint、build、test:ui。
   Expected: 全數通過；不呼叫正式 API／相機／DB，不增加 UI 功能。
4. 更新紀錄並 commit；全 UI 命令 task-done。
Review Focus：不能把拒絕呈現成空資料／零金額；其他網路錯誤仍有重試提示；使用者訊息以純文字顯示。
