# 財務寫入的重送與確認規則

適用批次：`20261020_0017`。本文件描述Transfer、群組結算與LINE入口的寫入保護，不代表正式部署或外部服務已驗收。

## Transfer與群組結算

`POST /api/transfer`、`POST /api/trips/:tripId/settlements`必須提供非空UUID `client_request_id`。沒有key或格式不合法時拒絕寫入；現有Web兩個寫入點已同步更新。內部舊manager相容方法仍能不帶key，但不是公開HTTP入口的重送契約；LINE多步驟相容流程由webhook event inbox保護。

`financial_commands`以使用者＋operation＋request ID唯一識別命令，保存canonical payload SHA256及原始結果。唯一insert與row lock保護多worker競爭，命令結果、帳戶異動與movement／settlement在同一DB transaction提交。callback失敗時連同key rollback，允許原request在問題排除後重試。

- 同key、同payload：回傳原始ID及`replayed=true`，不重複扣款或消除債務。
- 同key、不同payload：409，不建立另一筆，也不覆寫原結果。金額100、`"100.0000"`等價；UUID標準化，Transfer備註沿用既有trim／長度規則。
- 同key並行：只有一個執行者進入帳務寫入，其餘等待commit後重播結果。
- 不同key：代表不同使用者意圖；不以相同金額、日期或帳戶猜測去重。Transfer新增、編輯與刪除依固定UUID順序鎖住涉及的帳戶；既有Transfer的修改另鎖原紀錄，避免與新增交錯時讀到舊餘額。
- 已提交但HTTP回應遺失：沿用原key及payload重試。replayed回應不代表再次執行。
- 原Transfer刪除／群組結算撤銷後，舊key仍只回傳原ID，不復活舊資料。需要新操作時必須由使用者建立新意圖。
- 私人settlement posting仍是獨立概念：群組重播不修改任一側私人帳戶；active posting仍阻止撤銷，兩側反轉後才能撤銷。

Transfer成功維持200；群組結算初次201、重播200。兩者皆包含`data.<transfer_id|settlement_id>`與`replayed`。

Web在發送前將原payload／UUID保存於以登入使用者分隔的`sessionStorage`，直到收到成功回應才清除；未知結果時保留並帶回原資料。換頁／重整後可重試；整筆還款已使群組平衡時也保留待確認表單。400確認拒絕後可修改資料；401、409及未知失敗不自動換新key。關閉分頁、清除瀏覽器儲存或草稿損毀後，需先核對紀錄，不能宣稱一定能找回client key。

## LINE：確認前不建立自然語言收支

自然語言income／expense流程改為：解析→DB草稿→預覽→使用者明確postback確認→Transaction。預覽與交易是不同階段；`ai_parse_events.status=success`不是已記帳。

草稿保存於既有`ai_parse_events.parsed_payload.line_draft`，凍結日期、金額、類別、帳戶與幣別；只有同一Nomica使用者且source為line_bot可確認。30分鐘後逾期，取消／逾期／缺欄位／找不到指定帳戶均不建帳。確認鎖住草稿，以草稿UUID作交易request ID；不同postback event ID同時確認同一張卡也只建立一筆。確認與取消競爭時，以取得草稿鎖後的終態為準；已確認的取消不會反轉交易。

`line_webhook_events`以LINE `webhookEventId`唯一識別事件；缺event ID拒絕處理。fingerprint不包含會隨重送改變的reply token、isRedelivery及quote token。相同事件只解析／建立草稿／操作帳務一次，並保存可重播回應；同event ID換內容會拒絕。

事件處理結果與帳務先commit，之後才傳送LINE reply。reply失敗回503，讓LINE可重送；重送使用當次reply token傳遞原結果，不再記帳。簽章仍由現有SDK驗證，無效簽章400。交易中途失敗會rollback event inbox、交易、movement與草稿確認狀態，再以相同event ID重試。

local fallback取金額前先移除日期；「2026-10-01 午餐91元」預覽為91，不取2026。無法區分多個數字時不猜金額。這不證明外部模型準確率，也不取代AI quota／計費與隱私gateway。現有其他LINE多步驟選單的RAM state尚未整體遷移；本次持久化草稿保證針對自然語言收支確認，不宣稱所有選單流程均可跨worker續接。

## Migration與部署順序

先按既有備份流程套用`alembic upgrade head`至`20261020_0017`，再以協調批次更新backend/frontend。0017只新增`financial_commands`、`line_webhook_events`，不回填、更改或刪除現有交易、帳戶、movement與settlement。測試同時涵蓋空DB與帶帳務的0016升級。

**此批HTTP contract新增必填request key**；舊Web／第三方寫入client未升級時會得到400。正式切換前須確認寫入client已更新；未確認時維持舊client不可寫入，不以server自動生成key冒充重送保護。若需分段部署，先發布帶key的frontend（舊backend尚不提供冪等保證），再啟用新backend；過渡期間避免開放財務寫入。這是本批獨立相容性遷移計畫，不宣稱已在正式環境執行。

程式回退時保留新表與既有命令結果，不自動downgrade；刪除這兩張表會失去歷史去重能力。client不得因timeout重建key；event／command資料的正式保留與帳號刪除規則仍需與後續release治理一起決定，不能任意purge去重紀錄。

## 本批驗證範圍

正式回歸置於`tests/test_financial_command_idempotency.py`、`tests/test_line_durable_confirmation.py`及現有API／parser／migration tests。DB測試沿用顯式`RUN_DB_SMOKE_TESTS=1`與loopback `*_test` guard，會重建schema，只能在確認歸屬的獨立空測試DB執行。

另以本機實際Chrome→API→本輪獨立PostgreSQL驗證Transfer及整筆還款的「已提交→丟回應→重整→原key重試」，並以LINE profile/reply替身、實際HTTP與DB驗證重複事件及確認前零扣款。這些臨時runner、合成資料、憑證與證據不進版控。真LINE delivery、Gemini、正式登入與手機實機不在本批通過結論內。

## F05收尾：核心帳務寫入錯誤

帳戶新增／修改／刪除／校正、Transfer新增／修改／刪除、群組結算新增／修改／撤銷、私人posting／反轉、預算新增／刪除及日常交易新增／修改／刪除，共17個寫入入口統一處理未預期例外：先rollback，回500與一般錯誤訊息。server log只保留固定操作名稱與例外類型，不記錄SQL、bound parameters或原始exception字串。已知業務驗證ValueError保留提示；既有404驗證與冪等衝突409維持。

LINE webhook不記錄原始body，parser失敗也不記錄可能包含輸入或token的exception字串。`tests/test_financial_error_responses.py`涵蓋各入口的DB／未預期／驗證錯誤，並以實際DB驗證原始同帳戶轉帳被拒絕且零異動，以及第一側餘額更新後SQL失敗的完整rollback與原key重試。Flask test client使用隔離的Auth替身，不算真實登入驗收。

這次不新增migration，也不改帳務計算。此範圍不是全站錯誤回應稽核；其他查詢、旅行管理、配置及Auth入口仍需逐步檢查。正式環境設定與真實外部服務的結論維持未驗證。
