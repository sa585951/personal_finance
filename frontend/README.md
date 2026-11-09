# Nomica Web／PWA

Vue 3 + Vite。正式環境透過同源代理呼叫後端（見 `vercel.json`），不需要設定 API 網址。

## 本機開發

```bash
npm install
cp .env.example .env.local
npm run dev
```

本機變數：

- `VITE_APP_API_URL`：只在開發時使用的後端網址；預設由 Vite 代理 `/api` 到 `http://127.0.0.1:5000`（可用 `NOMICA_DEV_API_TARGET` 改）。
- `VITE_DEV_AUTH_BYPASS=true`：搭配後端 `DEV_AUTH_BYPASS=true`，略過 LINE 登入。只在 loopback 有效，正式 build 會拒絕。

## 檢查與測試

```bash
npm run lint
npm run check:styles   # 樣式守門：token、共用類別、重複選擇器
npm run build
npm run test:ui        # mock API 的 UI 回歸：5 種寬度 × 深淺色
npm run test:e2e       # 真實瀏覽器 → Vite → Flask → PostgreSQL；需 DATABASE_URL 指向本機資料庫
```

沒有安裝 Playwright 瀏覽器時，可加 `UI_BROWSER_CHANNEL=chrome` 改用本機 Chrome。

視覺規格見 [`../docs/visual-design-system.md`](../docs/visual-design-system.md)。
