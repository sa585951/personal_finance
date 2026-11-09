# LINE AI 口語記帳試用

常見格式沿用規則。其他記帳文字在使用者回「同意 AI」後，由 Google Gemini 解析。
第一句用來說明資料流，使用者同意後須重傳一次。每位使用者各自管理同意，可隨時回
「撤回 AI」。撤回後可繼續用規則記帳與確認既有草稿。已獲准處理的請求可能仍會送到 Google。預覽、選帳戶與確認沿用 LINE 草稿，確認前不入帳。

## 帳戶選擇

句子裡講到的帳戶（例如「國泰卡」）比對成功時直接帶入。否則顯示帳戶選單：只列本人、同幣別、使用中的帳戶，上次用過的排第一，接著是近 90 天最常用的，每頁 8 個，帳戶更多時有「更多帳戶」按鈕。選單出現後也可以直接回覆帳戶名稱（信用卡可簡稱「玉山卡」）。選定後仍要按確認才入帳；翻頁後前一頁的按鈕仍有效。

## 啟用

1. 使用既有部署環境與 LINE webhook。先將資料庫升級至 Alembic
   `20261109_0020`，再部署此版。由伺服器資料庫角色存取三張 AI 表。
2. 在 Google AI Studio 核對專案、帳務、Key 限制與資料使用條款。試用使用
   Paid Tier 的 Gemini Developer API Standard 文字價格。確認專案後，透過部署平台
   秘密設定保存 `GEMINI_API_KEY`，並設 `NOMICA_LINE_AI_PAID_PROJECT_VERIFIED=true`。請比對最新的 [Google Gemini 定價與資料使用表](https://ai.google.dev/gemini-api/docs/pricing)。
3. 每月費用上限預設為 5 USD，不需設定。要調整時設 `NOMICA_LINE_AI_MONTHLY_USD`
   （需至少 0.001792 USD 供首次預留）；設 `0` 會關閉 LINE AI，只用規則記帳。
   無法解析的值一律視為關閉。LINE 沿用原模式預設，Web AI 可維持 disabled。
4. 用自己的 LINE 帳號測試「幫助」、「午餐 120 現金」及「昨天跟同事吃午餐，刷國泰卡 120」。
   確認首次只顯示同意提示、重傳才出草稿、確認後只入帳一次，並在撤回後重測新訊息。
   用第二個已登入的 LINE 帳號核對其同意與帳本各自獨立。核對用量表與 Google 帳務。

## 監控與停用

費用依 UTC 月份計算，覆蓋這個資料庫中的所有 LINE Gemini 請求。每次先預留
4,096 輸入 Token 與 512 輸出 Token，後者含思考 Token。先用同一個模型執行
[Token 計數](https://ai.google.dev/gemini-api/docs/generate-content/tokens)再產生內容，
以回報用量結算。模型固定為 `gemini-3.1-flash-lite`。未知結果保留預留費用，
同一 LINE 事件不會再次呼叫。每個帳號的請求至少相隔五秒。此處金額是 Nomica 依
Standard 牌價估算的 API 成本，Google 帳務可能包含專案其他用途、稅金或費率變更。

唯讀監控查詢如下。表中沒有使用者訊息原文、Prompt 或模型回覆。

```sql
SELECT month, model, status, count(*) AS attempts,
       sum(input_tokens) AS input_tokens, sum(output_tokens) AS output_tokens,
       sum(charge_usd) AS charged_or_reserved_usd
FROM line_ai_attempts
GROUP BY month, model, status
ORDER BY month DESC, model, status;
```

需要停用時，由維運者執行 `UPDATE line_ai_control SET enabled = false WHERE id = 1`。
它會阻擋新請求取得發送授權，規則仍可用。已獲准處理的請求仍可能送出或完成。若收到超限的供應商用量，
系統會記錄並停用後續請求。核對原因和費用後才將 `enabled` 設回 `true`。

回退應用程式版本時，先停用 AI 並保留 migration 和用量資料，以免清掉當月已預留的費用。
