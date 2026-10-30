# 測試、問題修復與回歸狀態

日期：2026-10-30。保持 `codex/nomica-s3-fx-guard`，不 Push／Merge／建立 PR。
本文件是既定 S1～S6 的測試追蹤，不重排開發範圍。

## 已證實與已修復

| ID | 證據與狀態 | 尚缺驗收 |
| --- | --- | --- |
| R01 | 已修補不安全旅行／月報查詢組合 | 正式查詢隔離與部署證據 |
| R02/U06 | 已改純文字／DOM value；惡意對話框 UI regression 已有紀錄 | 正式版本／實機回歸 |
| R12/R13/R14 | OAuth state／nonce、同源 Cookie 與公開設定修補已提交 | 真 LINE、正式代理、手機 PWA |
| R03 | S2 帳戶與交易鎖已提交；前輪 475 passed | 正式負載、多實例及歷史 reconciliation |
| R04 缺匯率 | 2de71ff；前輪新增／修改先 RED 後 GREEN，完整後端 480 passed | 與其餘 R04 月報問題分開追蹤 |

以上表格的 475／480 是前輪證據。本輪在新專用 DB 重跑完整 suite，結果為 489 passed（原 480 + 新增 9），包含 migration smoke tests。

## 待重現與未驗證風險

| ID | 現有依據 | 本輪結論 |
| --- | --- | --- |
| R04 月報混幣 | calculate_monthly_report_expenses 對 converted_amount／converted_share_amount 直接聚合，未分幣別 | 已用合成 DB 重現：TWD 600 + USD 20 得到無幣別總額 620；本機 Bug 已依確認規則修補：非 TWD 拒絕，17 項針對測試通過；不宣稱正式資料影響已盤點 |
| R05 編輯換匯 | 未提供 exchange_rate 會再取預設值 | 已重現並修補，8 項新案例及完整 suite 514 passed；未回填歷史資料 |
| R06 分攤尾差 | 現有分攤與換算流程需驗證守恆 | 已重現儲存四捨五入不守恆並按確認規則修補；6 項案例與完整 520 passed |
| R07 帳戶改幣別 | update_account 可直接更新 currency | 待帶帳務的修改案例與零異動保護驗證；未修補 |
| 預設匯率表 | 靜態 preset，沒有本輪市場來源／時效驗證 | 不把預設值稱作即時或歷史市場匯率 |
| data/*.json | 來源、真實性與保留需求未確認 | 不刪除、不推定為合成 fixture |

AI／LINE 互動維持停用；G-AI 的費用、Key／Billing、隱私與額度驗收仍未完成。

## 測試案例與結果

| 類型 | 案例 | 對應測試／狀態 |
| --- | --- | --- |
| 正常 | 同幣別不需跨幣報價；既有 pair／顯式匯率持久化正確 | 新增純函式案例 5 passed；既有 DB 案例本輪通過 |
| 異常 | 缺匯率拒絕新增／修改，commit 後四張帳務表不變 | test_exchange_rate_guard.py 本輪 5 項隨完整 suite 通過 |
| 邊界 | 兩幣別皆受支援，不代表 pair 有報價：KRW↔USD、KRW↔EUR | 新增 4 passed，拒絕默認 1 |
| 回歸 | 缺匯率不影響既有交易／餘額；發票／Transfer／LINE draft 不重複寫入 | 本輪完整 suite 489 passed；不是正式 API／實機驗收 |
| 待驗證 | 同月 TWD 日常與 USD base 的旅行 split 不可直接相加；同幣別、exclude、無本人 split、刪除交易需維持原契約 | 混幣診斷已重現；exclude／無本人 split／刪除交易的針對性修補驗收仍待下批 |

本輪已執行 `tests/test_exchange_rate_boundaries.py`：**9 passed**。
執行時禁止所有 DB 與網路連線、關閉 dotenv；未修改 production code。
另已取得使用者同意，在新專用 DB 執行完整後端回歸：489 passed，零 skip。
R04 混幣另外以臨時 diagnostic 重現（1 項診斷執行成功）；這表示成功觀察錯誤，
不是月報驗收通過，不計入 489 個 regression。前端／實機本輪未測。

## QA DB 使用邊界

使用者指定容器 `nomica-qa-20261020-a15822` 已唯讀確認為 running、PostgreSQL 16、
loopback port 55432，掛載同名持久化 volume；設定的既有 DB 為
`nomica_scenario_20261020_a15822_test`。沒有連線或檢視既有 scenario DB 內容。

使用者已明確同意沿用容器並另建空 DB。已新建並先驗空的
`nomica_s3_r04_review_20261030_test`；runner 僅允許此 DB，並禁止外網。
此 DB 供後續合成資料測試保留，沒有移除或覆寫既有 scenario DB。
不得直接對舊 DB 執行 drop_all；不得停止／刪除此共用 QA 容器或 volume。
最新執行授權：每批驗證通過可自主 commit；僅遇需求歧義、未授權真實／破壞性操作等停止條件時詢問。


## Migration 核對

本地 `alembic heads`：`20261021_0018 (head)`，接在 `20261020_0017`。
0018 是 S1 OAuth state 表；S2、R04 匯率 guard 與本輪測試補強均未新增 migration。
本輪 suite 含空 DB 與既有版本升級案例。這不證明既有 QA／正式 DB 已套用 head；
未讀取那些 DB 的 alembic_version，也未對它們執行 upgrade。

## 本批交付邊界

只新增邊界測試與此追蹤文件，未修改業務程式、schema 或既有測試行為。
R04 月報混幣的下一批修補需維持交易原幣／旅行結算幣別／個人報表幣別分離，
不能直接把既有 converted_share_amount 重新標成 TWD，也不能沿用錯誤總額 620
作正式 regression 預期值。已獲使用者授權，測試補強驗證通過可自主 commit。


## R04 已確認規則

使用者已明確決定：第一版只提供 TWD 報表，應納入的非 TWD 旅行分攤必須
明確報錯，保留原始資料、不靜默漏算。此規則供下一批 R04 RED→GREEN 使用；
本次測試盤點 commit 尚未包含實作，不能宣告月報已修復。

R04 修補批次：完整後端 506 passed，17 項新案例；詳見 `docs/s3-fx-correctness.md`。
