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

local fallback取金額及清理標題前先移除日期；「2026-10-01 午餐91元」預覽為91、標題為「午餐」，不取2026，也不殘留日期分隔符號。千分位金額會完整移除，不在標題留下逗號。無法區分多個數字時不猜金額。這不證明外部模型準確率，也不取代AI quota／計費與隱私gateway。現有其他LINE多步驟選單的RAM state尚未整體遷移；本次持久化草稿保證針對自然語言收支確認，不宣稱所有選單流程均可跨worker續接。

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

後續收尾將同一原則擴至54個AI解析、查詢、旅行管理、配置與分析入口，與前述17個寫入入口共用`_api_operation_error`。未預期錯誤一律rollback、回500並只記操作與例外類型；原有明確業務驗證400／404及配置的資源不存在語意維持。舊版部分入口將DB失敗回400／404，現在改為500，client應視為未知結果並保留原提交識別，而非自動當成資料無效重建請求。

`tests/test_api_error_redaction.py`以Flask API與service邊界故障注入，逐一驗證這54個入口的DB例外、未知例外與驗證錯誤。這不是所有安全面的稽核；Auth/OAuth、framework層例外、provider SDK自身的logging，以及正式log保存政策不在本次API handler驗證範圍。沒有新增migration、改帳務計算或驗證正式部署／真實外部服務。

## S4.1：一般／旅行交易原始請求（2026-11-03）

BudgetManager.add_transaction 的帶 key 呼叫共用既有 financial_commands，operation 為
`transaction.create`。同一 DB transaction 保存 payload SHA256、原始結果與帳務異動。
不新增 migration；須先具備 0017 表（目前本地 chain head 0019），未更新任何既有 DB。

Canonical v1 包含日期、項目、金額、type／category、description／merchant、account／
trip／payer、original currency、顯式 rate 或省略標記、timezone、review status 與有效分攤意圖。
UUID、Decimal 格式與成員／allocation 順序標準化；不將 parse_event_id 等非帳務輔助資料納入。
省略的 rate／currency 保留省略語意，不在回放時重新查目前預設／旅行資料。指紋不可改用
編輯後交易重建；未來改 canonical 必須考慮版本相容，不能自動覆寫已存 hash。

同 key 不同意圖回 409 `REQUEST_PAYLOAD_CONFLICT`。舊 key 沒有原始 command 時回
409 `LEGACY_REQUEST_UNVERIFIABLE`，`data.transaction_id` 為本人既有交易 ID，含軟刪除；
需先核對，不能自動換 key、從現值猜指紋或再次寫入。混合舊／新 server 的 unique 衝突
亦不會替舊交易補造原始意圖。已保存的新 key 回放原結果，不復活刪除紀錄、不再次扣款。

Backend 初批曾保留公開 API 的 optional key 相容；此歷史狀態已由下述公開必填切換取代。日常／旅行持久恢復與本機必填驗收已完成；正式部署同步、其他入口盤點仍未完成，不能宣告全部S4或部署開放。
LINE draft／QR 走同一 manager；現有草稿／receipt 鎖與原子確認仍保留，公開開關不改。
新增 22 項真實合成 DB／Flask API 案例，完整後端 617 passed；Auth／Provider 為替身。

## S4.1：Web 原資料恢復與明確核對解除（2026-11-03）

日常與旅行支出在 POST 前使用既有 pendingFinancialCommand，按登入 user 與
`transaction:daily`／`transaction:trip:<tripId>` 分隔 sessionStorage。原始 payload
與 UUID 保存成功前不送出；reload 不自動提交，顯示凍結原資料並由使用者明確重試。
新增前核對目前登入者，登入者變更／儲存不可用時 fail closed。JSON snapshot 脫離
Vue 巢狀 reactive 資料；舊 view 不能覆寫新意圖，晚到回應只清除相符 request ID。

成功才清除對應 pending；只有「交易 POST 本身確定回400」可解除並修改資料。
認證 preflight 的400、401／409／500／網路失敗不冒充交易未提交。未確認時保留原
payload/key；切換模式、返回或reload均不自動換 key。Trip 使用獨立 scope 並檢查
切換後的 trip ID，避免舊回應清錯範圍。

僅 `LEGACY_REQUEST_UNVERIFIABLE` 且有既有交易 ID 時顯示核對解除控制：
先顯示 ID，勾選「我已核對既有紀錄」才能點「結束這次待確認請求」。這只清除
本機 pending，不 POST、不修改／刪除既有交易，也不自動提交新的一筆。下一次新
意圖仍需另填資料並明確送出。一般409／未知結果沒有此解除捷徑。

25 組 Chrome 真實 Vue／mock API 案例及五尺寸深淺色、長字串、核對按鈕可操作性
通過；styles／lint／build通過。截圖供目視，不是 golden-image 像素基準。
另以真實 localhost Chrome→Flask→PostgreSQL（原授權 QA DB 的獨立 schema）驗證
日常／旅行先實際201提交再丟回應，reload後相同payload/key回200／replayed，
每個意圖只有一筆交易／一筆movement／一筆command。legacy回409後明確解除零
額外寫入。獨立SQL：1000－legacy40－daily100－trip100＝760，reconciliation
1 matched／0 mismatch。Cookie/JWT/session為實際本機路徑，身份為合成建立；未驗真
OAuth／LINE／Gemini或實機。無新增migration，沒有升級舊scenario／正式DB。

### 審查補強：凍結點擊意圖與POST登入者綁定

旅行驗證後在任何確認／auth await前建立JSON snapshot，後續欄位或編輯模式變更
不影響此次提交。updated Web的POST另帶 `X-Nomica-Request-Owner`，Backend
與token/session認證的current_user_id比較，不符409 `REQUEST_OWNER_CHANGED`且
rollback，不以header選擇／授權另一owner。這封住preflight與POST之間換Cookie的
競態；舊client省略header仍相容，不冒稱其具備同等保護。
29組UI及620項Backend通過；真實本機A→B Cookie競態409，B零交易、原帳務不變。
使用者已核定公開交易key改必填；下述批次已實作，正式部署前仍須同步client。

### 公開交易key必填切換（已核定並本機實作）

POST /api/transactions拒絕missing/null/empty/非字串與invalid UUID key，回400、
rollback且不產生交易或command reservation。internal manager無key呼叫仍相容，
不因此宣稱那些呼叫具備重送保證。owner mismatch仍先409。
新增20個真實DB/API案例（含owner優先與internal控制）；10 regression先RED，
其他控制通過後修補。原數值、parse event與錯誤遮蔽測試補有效key，維持原意圖。
最終task-done完整Backend640 passed（60.02s），
完整29組恢復案例／原UI及styles/lint/build通過。
實際localhostAPI缺key400，正常daily/trip掉回應重整原key回放與legacy解除、
A→B Cookie409及獨立SQL回歸通過。部署前須同步所有寫入client、確認實際DBrevision，
過渡期不開放未更新client寫入。無新migration，未部署、未改正式資料。

公開交易key批次fresh review無新增Critical／Important／Minor。其他公開財務入口
仍未因此獲得相同保證：新增帳戶double-click已在攔截API的UI診斷觀察到兩次無key
POST；校正原始payload一致性／預算R08待原序驗收。沒有改這些API的相容行為。
