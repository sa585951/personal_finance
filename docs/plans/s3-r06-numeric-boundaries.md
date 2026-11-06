# S3.1 R06：finite／範圍／DB 精度驗證
Spec：原 S3.1 無效數值拒絕與 R06 finite／範圍／精度；沿既有 AMOUNT Numeric(18,4)、RATE Numeric(18,8)。
不新增商業精度規則、不改 JSON number 契約、不改既有原幣 minor-unit 邏輯。
明確金額／匯率超精度應拒絕，不交給 DB 靜默捨入；計算得出的換算金額可按既有四位 HALF_UP。

## Task 1: 交易與分攤數值在寫入前驗證
1. 純函式／真實 DB regression：NaN／Infinity、非法字串／None／bool、超 DB 精度／範圍及換算溢位。
   Expected: 現碼錯誤類型或接受無效值，RED；拒絕後 commit 亦零異動。
2. 最小共用 Decimal parse finite/type bounds validator；amount 保持正數，custom share 保持可0，rate 正數。
   Expected: 正常上限／精度及四位換算守恆不變，無效值皆 ValueError。
3. 針對測試及專用 runner tests -q 全套，Expected: 全通過且零 skip。
4. 更新合約／進度，通過後 commit、task-done。
Review Focus：先 finite 再比較／quantize；顯式 rate 不靜默捨入；計算額進 DB 前檢查範圍；custom zero 不誤擋；非法值不變成未知 DB 500。
