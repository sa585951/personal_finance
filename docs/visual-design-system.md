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

## 已套用與待驗收

這一批已套用 Web 語意色票、首頁摘要卡、導覽、登入頁、PWA 圖示、基本互動動態與平板斷點。Web 初次使用時依系統偏好選擇 Light/Dark；登入頁與主導覽有手動切換按鈕，選擇會保存在本機瀏覽器。其他頁面的常用中性色及狀態色已改用 token，複雜表單、旅行詳情、圖表和空狀態仍需以真實資料逐頁目視檢查。

上架前另需確認：390/430/768px 主要流程、真實資料長金額與長名稱、VoiceOver、Dynamic Type、色彩對比、深色模式決策、登入與 session lifecycle、正式 iOS 功能及 TestFlight。Web build/lint 或本文件都不代表 iOS 已可上架。iOS 功能範圍仍依 `docs/product-roadmap.md` 的 M6A–M6C 門檻。

圖示資產的來源與重產方式見上方「品牌標記與 LINE 頭像」。
