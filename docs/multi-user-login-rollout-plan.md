# Multi-user Login Rollout Plan

此文件整理多人旅行帳本從 dev-only 測試走向正式登入/部署前，需要確認與補強的項目。

## Current State

目前第一版已完成：

- owner 可建立、複製、關閉旅行邀請連結。
- 邀請連結路由為 `/trips/invite/:token`。
- 未登入使用者進入邀請連結時，Vue Router 會帶 `redirect` query 導到登入頁。
- LINE Login 入口會把 `redirect` 存到 `sessionStorage.post_login_redirect`。
- LINE callback 成功後，前端會導回原本的邀請連結。
- LINE Login 已改由後端發起並驗證 signed state，避免前端自行組 login URL 造成 callback / redirect 風險。
- owner / editor / viewer 權限第一版已完成：owner 管理帳本與全部交易，editor 管理自己建立的交易，viewer 僅可閱讀。
- 本地 dev-only 可用右上角測試使用者切換器模擬 `Dev User`、`Amy`、`Ben`、`Cara`。
- 後端只在 `DEV_AUTH_BYPASS=true` 且非 production 時接受 `X-Dev-User`。

Phase 5 收尾判定：

- LINE Login / 邀請連結 / 多人權限第一版可作為 MVP 測試基礎。
- iOS 主畫面 PWA 的 LINE Login 不穩定，不列為 Phase 5 主要解法；後續搭配同站網域、正式 session 架構或原生 App 再處理。
- Google / Apple Login 保留到商品化前再評估。

## Production Readiness Checklist

### 1. Auth Provider

MVP 可先採 LINE Login 作為正式邀請登入方式。

產品長期理念：

- 使用者未來可用 Google / Apple / Email 等方式建立主要帳號。
- LINE 不一定是唯一主帳號，而是建議加綁的快速記帳入口。
- 加綁 LINE 後，使用者可在 LINE Bot 內進行一般記帳、查詢與提醒，就像有一個個人記帳助理。

Phase 5 已採用：

- 第一版只支援 LINE Login。
- Google / Apple 不在 Phase 5 補入。
- schema 已透過 `user_identities` 支援多 provider，後續可在同一個 `users.id` 下加綁 LINE。

後續建議：

- Phase 5.5 先觀察 LINE / AI 快速記帳是否足以提高回訪。
- 正式商品化前再規劃 Google / Apple / LINE 加綁流程。

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

Phase 5 第一版已完成並可持續實測：

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

1. Phase 5.5 持續觀察 LINE / AI 快速記帳是否真的提高使用頻率。
2. 實測外部旅伴與登入旅伴並存是否會讓流程混亂。
3. 若真的需要，再規劃 owner 手動合併 member。
4. iOS PWA 登入問題移到 Phase 6 或正式 App 規劃，不再於 Phase 5 追加 workaround。
5. 後續商品化前，再規劃 Google / Apple / LINE 加綁流程。

## iOS Timing

正式 iOS 開發不建議現在開始；iOS 主畫面 PWA 登入問題也不作為 Phase 5 主要解法。

建議達成以下條件後再進入 iOS：

- Web/PWA 的日常記帳、旅行記帳、分帳、邀請加入都已穩定。
- 正式登入流程已可用，不依賴 dev-only 切換器。
- Phase 5 實際旅行測試後，確認哪些功能真的會用。
- UI 資訊架構不再大幅變動。

目前建議先把 Web / LINE / PWA 作為 Phase 5.5 的留存與效率驗證版本，iOS 放在 Phase 6 或 Phase 7。
