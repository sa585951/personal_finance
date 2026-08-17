# Nomica iOS Prototype

這是已完成第一輪驗證的 SwiftUI read-only prototype。它能啟動、呼叫 Nomica 後端 API，並顯示首頁摘要、最近收支與帳戶列表。

依 2026-08-17 的產品 Roadmap，iOS 功能開發暫停在此可運行基線。專案會先完成 M0 至 M5 的財務語意、Mobile Web、PWA Alpha、Ledger Correctness 與 PWA Beta，再於 M6 繼續正式 iOS Vertical Slice。

## 開啟方式

1. 安裝完整 Xcode。
2. 用 Xcode 開啟：

   ```text
   ios/Nomica/Nomica.xcodeproj
   ```

3. 選擇 `Nomica` scheme 與任一 iPhone Simulator。
4. 按 `Run`.

## 本地後端

目前 App 預設呼叫：

```text
http://127.0.0.1:5001
```

請先在專案根目錄啟動後端，並開啟 dev auth：

```bash
env DATABASE_URL=postgresql://personal_finance:personal_finance@localhost:5433/personal_finance FLASK_ENV=development DEV_AUTH_BYPASS=true FRONTEND_BASE_URL=http://127.0.0.1:5174 VITE_BACKEND_BASE_URL=http://127.0.0.1:5001 .venv/bin/flask --app web_app run --host 127.0.0.1 --port 5001
```

Simulator 通常可以呼叫 Mac 的 `127.0.0.1`。若未來改用實機測試，請把 App 上方的 API Base URL 改成 Mac 的區網 IP，例如：

```text
http://192.168.1.20:5001
```

## 第一版範圍

- 不做 Apple Login。
- 不做 TestFlight。
- 不做 Keychain。
- 不做新增、編輯、刪除。
- 使用 `X-Dev-User` header 測 `Dev User / Amy / Ben / Cara`。
- 先讀取 `/api/auth/me`、`/api/dashboard/overview`、`/api/assets`、`/api/transactions`。

## 目前畫面

- 首頁：本月收入、支出、結餘、最近紀錄。
- 收支：最近 30 筆收支。
- 帳戶：帳戶名稱、類型、幣別、餘額。

## 目前暫停點

- 已完成 `SessionGateView` 與 API 登入狀態檢查。
- `KeychainStore` 是尚未接入 `AppSession` 的探索草稿，不代表 token persistence 已完成。
- 正式 JWT／Keychain、Sign in with Apple、LINE Login、session expiry／logout／revocation 統一移到 M6A。
- M6B 再實作 Login、Home、Quick Add、Transaction 與 Trip 的第一條 mobile vertical slice。
- M6C 才進入 TestFlight 測試。

完整順序見 `../../docs/product-roadmap.md`。
