# Multi-user Login Rollout Plan

此文件整理多人旅行帳本從 dev-only 測試走向正式登入/部署前，需要確認與補強的項目。

## Current State

目前已完成：

- owner 可建立、複製、關閉旅行邀請連結。
- 邀請連結路由為 `/trips/invite/:token`。
- 未登入使用者進入邀請連結時，Vue Router 會帶 `redirect` query 導到登入頁。
- LINE Login 入口會把 `redirect` 存到 `sessionStorage.post_login_redirect`。
- LINE callback 成功後，前端會導回原本的邀請連結。
- 本地 dev-only 可用右上角測試使用者切換器模擬 `Dev User`、`Amy`、`Ben`、`Cara`。
- 後端只在 `DEV_AUTH_BYPASS=true` 且非 production 時接受 `X-Dev-User`。

## Production Readiness Checklist

### 1. Auth Provider

MVP 可先採 LINE Login 作為正式邀請登入方式。

產品長期理念：

- 使用者未來可用 Google / Apple / Email 等方式建立主要帳號。
- LINE 不一定是唯一主帳號，而是建議加綁的快速記帳入口。
- 加綁 LINE 後，使用者可在 LINE Bot 內進行一般記帳、查詢與提醒，就像有一個個人記帳助理。

需要確認：

- 是否接受第一版只支援 LINE Login。
- 是否要在部署前就加入 Google Login。
- 未來若做 iOS App，是否仍以 LINE 作為主要登入，或改成 Apple / Google / LINE 多 provider。

目前建議：

- 出國前朋友共用版本先用 LINE Login，因為與既有 LINE Bot / LINE Login 最接近。
- Google / Apple 保留到正式商品化前再做，避免 Phase 5 範圍失控。
- schema 已透過 `user_identities` 支援多 provider，後續可在同一個 `users.id` 下加綁 LINE。

### 2. OAuth State Verification

目前已改為後端發起 LINE Login：

- 前端導向 `/line-login-start?redirect=...`。
- 後端產生 signed `state`，內容包含站內 redirect path 與過期時間。
- LINE callback 時後端驗證 `state`，再把 app JWT 與 redirect path 帶回前端 `/auth-callback`。
- redirect path 只允許前端站內路徑，避免 open redirect。

風險：

- 正式 OAuth 流程應驗證 `state`，降低 CSRF / login flow injection 風險。

目前採用的是較乾淨方案，適合 Phase 5 進入正式登入測試前先完成。

### 3. Invite Link After Login

目前流程：

1. 使用者打開 `/trips/invite/:token`。
2. 未登入時導到 `/login?redirect=/trips/invite/:token`。
3. 登入頁導向後端 `/line-login-start`。
4. 後端用 signed state 保存 invite redirect path。
5. LINE Login 成功後導回原 invite URL。
6. `TripInviteAccept` 呼叫 `POST /api/trip-invites/:token/accept`。
7. 加入成功後導到 `/trips?trip_id=...`。

需要實測：

- 一般視窗 owner 建立 invite。
- 無痕視窗未登入打開 invite。
- LINE Login 成功後是否回到 invite URL。
- 接受邀請後是否進入正確 trip。

### 4. External Member Merge

目前接受邀請會建立或重新啟用登入使用者自己的 `trip_members`。

不會自動合併：

- owner 手動新增的外部旅伴 `Amy`
- 真實登入後接受邀請的 `Amy`

原因：

- 同名不一定同人，自動合併可能造成分帳資料誤綁。

需要討論：

- Phase 5 實測是否接受「外部旅伴」與「登入旅伴」並存。
- 是否要做 owner 手動合併功能。
- 合併前是否需要顯示該 member 已有付款、分攤、結算紀錄。

目前建議：

- Phase 5 不做自動合併。
- 若真的需要，先做 owner 手動合併，並加上高風險確認。

### 5. Production Environment Flags

正式部署必須確認：

- Backend `FLASK_ENV=production`
- Backend `DEV_AUTH_BYPASS=false`
- Frontend `VITE_DEV_AUTH_BYPASS=false`
- Backend `FRONTEND_BASE_URL` 指向正式前端網址
- Backend `VITE_BACKEND_BASE_URL` 指向正式後端網址
- Frontend `VITE_APP_API_URL` 指向正式後端網址
- LINE Login console 的 callback URL 設為正式後端 `/line-login-callback`

注意：

- dev-only `X-Dev-User` 在 production 不會生效。
- 前端右上角測試使用者切換器在 `VITE_DEV_AUTH_BYPASS=false` 時不會顯示。

## Suggested Next Steps

1. 在本地關掉 dev bypass，用 LINE Login 實測 invite redirect。
2. 若本地 LINE callback 不方便測，先部署 staging，再測正式 invite 流程。
3. 實測外部旅伴與登入旅伴並存是否會讓流程混亂。
4. 再決定是否補 owner 手動合併 member。
5. 後續商品化前，再規劃 Google / Apple / LINE 加綁流程。

## iOS Timing

正式 iOS 開發不建議現在開始。

建議達成以下條件後再進入 iOS：

- Web/PWA 的日常記帳、旅行記帳、分帳、邀請加入都已穩定。
- 正式登入流程已可用，不依賴 dev-only 切換器。
- Phase 5 實際旅行測試後，確認哪些功能真的會用。
- UI 資訊架構不再大幅變動。

目前建議先把 Web/PWA 作為 Phase 5 實戰版本，iOS 放在 Phase 6 或 Phase 7。
