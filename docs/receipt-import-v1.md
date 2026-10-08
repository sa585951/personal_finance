# 發票掃描記帳 V1

入口：`/add?mode=receipt`，也可從新增收支選「掃描發票記帳」。相機需 HTTPS 或 localhost；選圖片支援 JPEG／PNG／WebP，最大 10 MB。請掃左側 QR，圖片含兩個 QR 時可裁切左側後重試。

只支援台灣電子發票日常支出；官方左側固定 header 不包含店名／消費時間，店名由使用者補填。解析是結構驗證，不能證明發票真偽或未作廢。0 元發票不建立支出。無 OCR、商品明細、旅行分帳、批次或載具 API。

發票以使用者＋號碼＋開立日＋賣方統編唯一識別，相機與圖片共用。重複掃描不新增發票；已連結時不新增交易。疑似手動紀錄以相同 TWD 金額與前後一天比對，最多五筆，必須人工選擇。連結不修改原交易；建立會原子保存交易、帳戶 movement 及發票連結。忽略可再次掃描後重新開啟，稍後處理可再次掃描繼續。

發票日期與金額在新增表單唯讀，由後端固定；付款帳戶僅顯示 TWD，可選不連動帳戶。已連結交易被軟刪除後，重新掃描／處理會回到 pending，重新建立使用新的 request ID。原 QR、圖片、隨機碼與加密區不保存；發票 API 不記錄 payload 或回傳內部例外。

## 部署與驗收

先備份並依既有流程套用 `alembic upgrade head`（`20261008_0016`），再部署 backend、frontend。此 migration 只新增 receipt 表，不回填或修改既有交易。Downgrade 會刪除 receipt 關聯資料，正式 rollback 應優先回退程式並保留表，不直接 downgrade。

本機驗證：pytest、指定本機 `*_test` 的發票／migration／既有 schema smoke，及 frontend lint/build。390／430px headless Chrome 使用合成 QR 與 mock API 驗證圖片解碼、相機拒絕備援、唯讀欄位、單次提交與無水平溢出；不等同實機相機或正式部署驗收。

上線前仍需在 iPhone Safari／PWA 與 Android Chrome／PWA 驗證：授權與拒絕相機、左右 QR、圖片備援、取消或返回時相機關閉、網路失敗重試、重掃不重複扣款。使用非敏感測試發票並確認帳戶異動。

未來載具來源以同一發票身分 upsert；官方資料晚到只補全發票資訊，不自動覆寫手動交易。下一批再設計待確認列表與逐筆原子化的批次 resolve。
