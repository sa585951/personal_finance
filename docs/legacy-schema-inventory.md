# Legacy Schema Inventory

更新日期：2026-08-21

## 目的

本文件記錄 M3E 對舊資料模型與執行入口的盤點結果。原則是先隔離、停止新寫入並保留既有資料；只有在確認匯出、轉換與刪除策略後，才執行破壞性 migration。

## 已隔離

| 項目 | 目前狀態 | 處理決議 |
| --- | --- | --- |
| `assets` legacy table | 只有 `legacy_metadata` 定義；目前 `AssetManager` 使用新版 `accounts` table | 保留定義供舊資料盤點，不允許 active API 存取 |
| `budget_months`／`budget_categories` legacy tables | 只有 `legacy_metadata` 定義，專案沒有其他程式引用 | 保留定義供舊資料盤點；目前預算流程使用新版 schema |
| `goals` legacy table | 定義於 `legacy_metadata`，不屬於目前 Alembic metadata | 保留資料；產品流程停止讀寫 |
| `/api/goals` | 舊 CRUD 路徑 | 保留 authenticated `410 Gone` 相容回應 |
| `/api/reports/goal_summary` | 舊 Goals 報表路徑 | 保留 authenticated `410 Gone` 相容回應 |
| Web `/goals` | 舊書籤可能仍存在 | 導向 `/analysis`，移除未使用 Goals chunk 與元件 |
| LINE Goals 指令 | Active handler 已回傳功能暫停提示 | 維持停用；Rich Menu 建立腳本不再建立 Goals 按鈕 |
| `models/goal_manager.py` 與 dormant LINE goal handlers | 尚有 legacy import 關係，但不在 active Web／LINE runtime 路徑 | 暫時保留並標示隔離；等資料處理決議後一併刪除 |

## 仍在使用，不可移除

| 項目 | 使用原因 | 後續條件 |
| --- | --- | --- |
| `trips.include_in_monthly_report` | TripMember 偏好 migration 與舊客戶端相容仍會讀寫 | 所有部署版本只使用 member preference 後再評估移除 |
| `transactions.review_status` | 旅行交易確認狀態與前端顯示仍使用 | 需另開資料語意與 UI 收斂批次 |
| Transaction type 的 `transfer`／`adjustment` 相容值 | 舊資料與 schema contract 仍可能存在 | 完成資料掃描與轉換前保留 |

## 尚待處理但不阻塞 M3

- Supabase 是否仍存在 `assets`、`budget_months`、`budget_categories`、`goals` 舊資料；檢查前不得直接 drop。
- dormant LINE goal flow、theme helper 與 `reports/financial_reports.py` 的安全刪除範圍。
- Goals 舊資料是否需要匯出、轉成 Bucket／Purpose，或在帳號刪除政策中一併清理。

## 安全邊界

- 本批沒有 migration，也不刪除任何正式資料。
- Goals 相容端點仍要求有效 session，避免未登入者利用舊路徑探測帳號資料。
- `410 Gone` 明確表示功能已退役；呼叫端不應把它當成可重試的暫時性 `500`。
