# Nomica 視覺設計基準

更新：2026-10-06。這份文件定義 Web/PWA 已開始採用的視覺方向，供後續 SwiftUI 垂直流程沿用。它不是 iOS 上架驗收紀錄。

## 產品語氣

Nomica 是日常收支、帳戶與旅行分攤的同一本帳。採用「Calm Finance with Travel Accent」：主要財務流程以中性底色與 Indigo 建立安定、精確的閱讀節奏；旅行情境才使用 Aqua。收入與正向狀態用 Green、支出與負向狀態用 Red、待處理事項用 Amber。避免把 Green 或 Red 當品牌色。

## 共用樣式

| 用途 | Light | Dark | Web token |
| --- | --- | --- | --- |
| 頁面背景 | `#F7F8FA` | `#101216` | `--page-bg` |
| 主要表面 | `#FFFFFF` | `#181B21` | `--card-bg` |
| 次要表面 | `#F0F2F5` | `#21252C` | `--secondary-color` |
| 主要文字 | `#171A1F` | `#F4F5F7` | `--text-color` |
| 次要文字 | `#6F7682` | `#A4AAB4` | `--light-text-color` |
| 邊框 | `#E2E5E9` | `#2D323A` | `--border-color` |
| 品牌與主要操作 | `#4263EB` | `#748FFC` | `--primary-color` |
| 旅行與外幣 | `#2F9EAF` | `#4CC9C0` | `--travel-color` |
| 收入與正向狀態 | `#23856D` | `#4CC39A` | `--income-color` |
| 支出與負向狀態 | `#D95353` | `#FF7373` | `--expense-color` |
| 提醒 | `#D98E04` | `#F5B84B` | `--warning-color` |

深色模式的主要文字使用 `#F7F8FA`，次要文字使用 `#BEC4CE`；瀏覽器字體平滑維持系統預設，避免小尺寸繁體中文字在深色背景上顯得過細。AI 解析區使用獨立的 `--ai-surface`、`--ai-surface-raised`、`--ai-border` 與 `--ai-accent`，在 Light/Dark 使用不同表面層級，不以固定淺藍色跨模式顯示。

### Web 共用 UI 類別

`frontend/src/assets/style.css` 管理主題 token 與全站基準；`frontend/src/assets/ui.css` 管理需明確加上 class 才生效的共用樣式，由 `main.js` 載入。主要頁面、旅行操作與配置表單已逐步採用，不會自動替換沒有加上 class 的元件。

- `app-card`：卡片表面、邊框、圓角與陰影；不設定內距或排版。
- `app-surface`：既有頁面卡片的表面樣式，不設定文字顏色或邊框寬度；取代原本依賴頁面 class 名稱的高權重 `#app` 覆寫。
- `app-primary-action`：僅提供主要操作的配色與圓角，保留既有控制項尺寸與排版；新控制項優先使用完整的 `app-button`。
- `app-chart-card`：共用既有圖表／提醒卡的表面、內距與間距，保留原本視覺規格。
- `app-form-fields`／`app-field-labels`：配置表單的共用欄位／僅標籤樣式。使用低權重 `:where()`，帳戶選擇器、金額組合輸入框與各表單斷點仍由 component 控制。
- `app-button`：基本按鈕／連結、44px 最小高度、圖示、disabled 與鍵盤焦點；搭配 `app-button--primary`、`app-button--soft`、`app-button--text`。
- `app-notice`：狀態訊息內距與字級；搭配 `app-notice--info`、`app-notice--error`。`role="status"`／`role="alert"` 仍由 template 提供。
- 按鈕局部差異可透過 `--app-button-padding`、`--app-button-radius`、`--app-button-weight`、`--app-button-gap` 調整，避免複製整份宣告。

頁面 grid、導覽定位、相機框線與候選交易排版繼續放在 component 的 scoped CSS。後續移轉其他頁面應逐批替換並檢查深淺色、hover、focus、disabled 與手機版面；不要一次以全域 `button` selector 覆寫既有元件。

警告文字使用 `--warning-text`，警告色標與邊框使用 `--warning-color`。首頁深色 hero 上的白字／透明色、品牌資產及使用者自選色票不是一般中性色，不能機械式全部替換。

### CSS 與 UI 回歸檢查

在 `frontend` 執行：

```sh
npm ci
npm run check:styles
npm run lint
npm run build
npx playwright install chromium
npm run test:ui
```

macOS 已安裝 Chrome 時也可用 `UI_BROWSER_CHANNEL=chrome npm run test:ui`。測試自動啟動本機 Vite（127.0.0.1:4174）、隔離 `.env.local` 的 API／開發登入設定，結束後關閉服務。若需使用已啟動的本機 Vite，可指定 `UI_BASE_URL=http://127.0.0.1:5176`；只允許 loopback URL。

所有 `/api/` 請求都由 mock 攔截，其他外部請求會被阻擋，且預設不允許寫入操作。測試涵蓋 320／390／430／768／1280px 的深淺色主要頁面、配置表單、焦點、外觀偏好保留、選單操作、相機拒絕備援與 loading／error／retry。截圖輸出於 `frontend/test-results/ui`（不納入 Git），供目視檢查；目前不是像素差異 golden-image 測試，也不代表真實裝置相機或正式 API 整合驗收。

`check:styles` 驗證 CSS 可解析、首頁／Navbar 不重新累積相同層級的 selector 與 property 覆寫、共用 UI 不使用 ID selector，並防止恢復本批已移除的按鈕／表面覆寫。它不是完整的 Stylelint 或 accessibility audit。

本批已移除依頁面名稱指定的卡片與主要按鈕全域覆寫；全站頁面尺寸、輸入框基準、旅行配色與響應式配置仍保留在 `style.css`。不將所有重複的 flex／grid 宣告強制抽成工具 class；其他頁面的局部樣式仍可按需求分批收斂。

## 品牌標記與 LINE 頭像

Nomica 使用同一個「N」標記：兩條白色直柱代表穩定的帳目結構，Aqua 斜線代表從日常記帳延伸到旅行的流動。完整圖示使用 Indigo 方形底；保留四周留白，縮小到 32px 或裁成圓形時仍能辨認。圖示內不放產品名稱或 LINE 商標；名稱由介面文字或 LINE 帳號名稱呈現。

- 主標記：`frontend/public/nomica-mark.svg`，供 Web 導覽與登入頁使用。
- PWA、Apple touch icon、favicon：`frontend/public/app-icon-*.png`、`apple-touch-icon.png`、`favicon.png`、`favicon.ico`，與主標記相同。
- LINE 官方帳號頭像候選：`frontend/public/nomica-line-profile-640.png`（640×640px）。LINE 官方文件列出此尺寸，頭像需在 LINE Official Account Manager 上傳；存放在程式庫不會自動更新線上帳號。`frontend/public/line-logo.png` 是 LINE 平台圖示，不是 Nomica 品牌頭像。
- 修改標記時，同步更新 SVG 與 `frontend/scripts/generate_app_icons.swift` 的幾何，然後在 `frontend` 執行 `swift -module-cache-path /private/tmp/nomica-swift-module-cache scripts/generate_app_icons.swift public` 重產所有 PNG 與 ICO。

SwiftUI 應以 Asset Catalog 的語意色彩資源對應上表，由系統外觀自動切換，避免把 Web CSS 色值直接散落在 View 中。字體沿用系統字體與繁體中文 fallback。頁面標題約 28–34pt、正文 16pt、輔助文字 12–14pt；金額使用 tabular figures。卡片圓角 12–16pt，控制項 12–14pt。互動區至少 44×44pt。主要資訊不要只靠顏色區分。

## 動態與狀態

- 切頁淡入與短距離位移約 360ms；按鈕回饋約 180ms；比例條約 320ms。
- 支援系統「減少動態效果」，停用非必要轉場。SwiftUI 應對應 `accessibilityReduceMotion`。
- Loading、empty、error 都要顯示清楚的原因與下一步；登入、記帳、旅行分攤不得靠動畫掩蓋等待或重送狀態。
- 底部導覽使用五個既有入口；帳號設定維持獨立入口。安全區與鍵盤遮擋需在裝置上確認。
- 圖表類別色由 `--chart-1` 至 `--chart-8` 提供低飽和度的跨模式色票；Canvas 圖表在外觀切換時更新顏色。

## 響應式配置

- 手機（小於 700px）：單欄內容與底部導覽。
- 平板（700–1023px）：底部導覽；首頁摘要與提醒雙欄、旅行表單與列表雙欄；帳戶卡片可並排。收支與新增頁擴至適合閱讀的欄寬。
- 桌面（1024px 起）：頂部導覽，內容仍維持最大寬度，避免表單與財務數字過度拉長。分析頁於 900px 起並排預算與旅行摘要。
- 斷點是排版決策，不是裝置型號判斷；橫向平板在 1024px 以上會使用桌面導覽。

帳戶資金總覽的幣別與金額分開排版，必要時幣別另起一行，完整數字不從千分位群組中間斷行。長金額字級依卡片可用寬度調整，保留正負號、千分位與既有幣別小數規則。F06修復已用12位整數、USD兩位小數及負餘額JPY合成資料，驗證320／390／430／768／1280px深淺色的單行數字、無橫向溢出與鍵盤展開；此為mock視覺驗證，不代表真實API或手機實機驗收。

## 已套用與待驗收

這一批已套用 Web 語意色票、首頁摘要卡、導覽、登入頁、PWA 圖示、基本互動動態與平板斷點。Web 初次使用時依系統偏好選擇 Light/Dark；登入頁與主導覽有手動切換按鈕，選擇會保存在本機瀏覽器。其他頁面的常用中性色及狀態色已改用 token，複雜表單、旅行詳情、圖表和空狀態仍需以真實資料逐頁目視檢查。

上架前另需確認：390/430/768px 主要流程、真實資料長金額與長名稱、VoiceOver、Dynamic Type、色彩對比、深色模式決策、登入與 session lifecycle、正式 iOS 功能及 TestFlight。Web build/lint 或本文件都不代表 iOS 已可上架。iOS 功能範圍仍依 `docs/product-roadmap.md` 的 M6A–M6C 門檻。

圖示資產的來源與重產方式見上方「品牌標記與 LINE 頭像」。
