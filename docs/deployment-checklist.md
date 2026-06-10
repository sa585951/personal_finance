# Deployment Checklist

此文件整理 Phase 5 staging / friend test 部署前需要設定的環境變數、資料庫重建方向與部署後檢查項目。

## Deployment Goal

目前建議先做：

> Phase 5 staging deployment / friend test

也就是部署給自己與少數朋友測真實 LINE Login、邀請連結、多人旅行帳本與分帳流程。

目前不建議直接視為正式 production release。

## URL Rules

邀請連結由後端使用 `FRONTEND_BASE_URL` 產生。

本地：

```text
http://127.0.0.1:5174/trips/invite/<token>
```

部署後：

```text
https://你的前端網域/trips/invite/<token>
```

所以只要後端部署平台的 `FRONTEND_BASE_URL` 設成正式前端網址，邀請連結就不會是 localhost。

## Local `.env`

位置：

```text
/Users/zhefile/Projects/personal_finance/.env
```

用途：

- 本地後端 Flask
- 本地 Alembic migration
- 本地 dev / smoke test

可參考：

```text
/Users/zhefile/Projects/personal_finance/.env.example
```

需要設定：

```env
FLASK_ENV=development
PORT=5001
FRONTEND_BASE_URL=http://127.0.0.1:5174
VITE_BACKEND_BASE_URL=http://127.0.0.1:5001
DEV_AUTH_BYPASS=true

DATABASE_URL=postgresql://personal_finance:personal_finance@localhost:5433/personal_finance

JWT_SECRET_KEY=本地測試用-secret

LINE_LOGIN_CHANNEL_ID=你的 LINE Login Channel ID
LINE_LOGIN_CHANNEL_SECRET=你的 LINE Login Channel Secret

LINE_MSG_CHANNEL_ACCESS_TOKEN=你的 LINE Messaging API Channel Access Token
LINE_MSG_CHANNEL_SECRET=你的 LINE Messaging API Channel Secret

GEMINI_API_KEY=你的 Gemini API Key
GEMINI_MODEL=gemini-3.1-flash-lite
```

本地多人 dev 測試時：

```env
DEV_AUTH_BYPASS=true
```

本地測正式 LINE Login 時：

```env
DEV_AUTH_BYPASS=false
```

## Local frontend `.env`

位置：

```text
/Users/zhefile/Projects/personal_finance/frontend/.env
```

可參考：

```text
/Users/zhefile/Projects/personal_finance/frontend/.env.example
```

本地 dev bypass 測試：

```env
VITE_APP_API_URL=http://127.0.0.1:5001
VITE_DEV_AUTH_BYPASS=true
```

本地測正式 LINE Login：

```env
VITE_APP_API_URL=http://127.0.0.1:5001
VITE_DEV_AUTH_BYPASS=false
```

備註：

- `VITE_LINE_LOGIN_CHANNEL_ID` 目前前端不再直接組 LINE OAuth URL，登入改由後端 `/line-login-start` 發起。
- 若 `.env.example` 仍保留 `VITE_LINE_LOGIN_CHANNEL_ID`，不影響目前流程。

## Frontend Deployment Env

位置：

Vercel 專案設定：

```text
Vercel Dashboard -> Project -> Settings -> Environment Variables
```

Production / Preview 都建議設定：

```env
VITE_APP_API_URL=https://你的後端網址
VITE_DEV_AUTH_BYPASS=false
```

確認事項：

- 不要把 `VITE_APP_API_URL` 指到 localhost。
- 不要在部署環境開 `VITE_DEV_AUTH_BYPASS=true`。

## Backend Deployment Env

位置依你使用的平台而定，例如：

- Render: Dashboard -> Service -> Environment
- Railway: Project -> Service -> Variables
- Fly.io: Secrets
- 其他平台：Environment Variables / Config Vars

Production / staging 需要設定：

```env
FLASK_ENV=production
DEV_AUTH_BYPASS=false

DATABASE_URL=你的 Supabase PostgreSQL connection string

JWT_SECRET_KEY=正式強密碼

FRONTEND_BASE_URL=https://你的前端網址
VITE_BACKEND_BASE_URL=https://你的後端網址

LINE_LOGIN_CHANNEL_ID=你的 LINE Login Channel ID
LINE_LOGIN_CHANNEL_SECRET=你的 LINE Login Channel Secret

LINE_MSG_CHANNEL_ACCESS_TOKEN=你的 LINE Messaging API Channel Access Token
LINE_MSG_CHANNEL_SECRET=你的 LINE Messaging API Channel Secret

GEMINI_API_KEY=你的 Gemini API Key
GEMINI_MODEL=gemini-3.1-flash-lite
```

重要：

- `FRONTEND_BASE_URL` 會影響邀請連結。
- `VITE_BACKEND_BASE_URL` 會影響 LINE Login callback 的 redirect URI。
- `DEV_AUTH_BYPASS=false` 必須確認。
- `JWT_SECRET_KEY` 不可使用本地測試值。

## Supabase

位置：

```text
Supabase Dashboard -> Project Settings -> Database
```

你需要取得：

```text
PostgreSQL connection string
```

用途：

- 填到後端部署平台的 `DATABASE_URL`
- 本機跑 Alembic migration 時也會用到

若要從本機對 Supabase 跑 migration：

```bash
DATABASE_URL="你的 Supabase connection string" .venv/bin/alembic upgrade head
```

因為目前 schema 已大改，且舊 production 資料你已表示可刪，建議策略是：

1. 先備份 Supabase 舊資料。
2. 清掉舊 tables。
3. 對 Supabase 跑 Alembic migration。
4. 寫入 seed data。
5. 再部署後端。

注意：

- 不要讓新版後端直接連舊 schema，API 很可能會因缺 table / column 失敗。
- 若 Supabase 使用 Transaction Pooler，Alembic migration 建議用 direct connection 或 session pooler，避免 migration 行為被 pooler 影響。

## LINE Developers

位置：

```text
LINE Developers Console
```

需要確認兩類 Channel：

### LINE Login Channel

設定 callback URL：

```text
https://你的後端網址/line-login-callback
```

本地測試正式 LINE Login 時 callback URL 需能連到本地後端，通常需要 ngrok 或其他 tunnel：

```text
https://你的-ngrok-url/line-login-callback
```

### Messaging API Channel

Webhook URL：

```text
https://你的後端網址/line-webhook
```

需要確認：

- Webhook enabled
- Channel access token 已填到後端部署平台
- Channel secret 已填到後端部署平台

## GitHub / Auto Deploy

如果你的前端/後端平台都已綁 GitHub，push 後會自動部署。

但在 push 前建議確認：

1. Supabase schema 已準備好。
2. 後端 env 已填好。
3. 前端 env 已填好。
4. LINE callback URL 已改好。
5. 本地測試通過：

```bash
pytest -q

cd frontend
npm run build
```

## Deploy Order

建議順序：

1. 備份 Supabase 舊資料。
2. 清空 / 重建 Supabase schema。
3. 對 Supabase 跑 Alembic migration。
4. 寫入 seed data。
5. 設定後端部署平台 env。
6. 設定前端 Vercel env。
7. 設定 LINE Developers callback / webhook URL。
8. Push GitHub 觸發部署。
9. 檢查後端 healthcheck。
10. 開前端正式網址測登入。
11. 建立旅行邀請連結，確認連結不是 localhost。
12. 找朋友用 LINE 點邀請連結測加入。

## Post-deploy Smoke Test

部署後至少測：

1. 前端首頁可開。
2. LINE Login 可登入。
3. 登入後可看到帳戶 / 收支 / 旅行頁。
4. 建立旅行帳本。
5. 建立邀請連結。
6. 邀請連結使用正式前端網址。
7. 朋友可用 LINE Login 加入帳本。
8. owner 可調整朋友 editor / viewer。
9. editor 可新增自己的旅行支出。
10. viewer 看不到新增支出入口。
11. 分帳建議顯示正確。
12. 只有 owner 或付款方本人可按已付款。

## Current Open Decisions

目前已決定：

- Phase 5 先支援 LINE Login。
- 未來可支援其他 provider 作為主登入，再建議使用者加綁 LINE 作快速記帳入口。
- 外部旅伴與登入使用者先不自動合併。

仍待部署後觀察：

- 外部旅伴與登入旅伴並存是否會讓使用者混淆。
- 是否需要 owner 手動合併 member。
- 是否要在 Phase 5 就補 Google Login。
- 是否要建立 staging 與 production 兩套 Supabase 專案。
