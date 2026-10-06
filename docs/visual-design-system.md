# Nomica 視覺設計基準

更新：2026-10-06。這份文件定義 Web/PWA 已開始採用的視覺方向，供後續 SwiftUI 垂直流程沿用。它不是 iOS 上架驗收紀錄。

## 產品語氣

Nomica 是日常收支、帳戶與旅行分攤的同一本帳。畫面應清楚、安定，讓金額與下一步操作先被看見。介面用深綠表達可靠與掌握感，暖白保留呼吸空間；只有待處理、錯誤或財務正負語意才使用警示色。

## 共用樣式

| 用途 | Web token / 色值 | SwiftUI 對應建議 |
| --- | --- | --- |
| 主要操作 | `--primary-color: #116F67` | `Color(red: 17/255, green: 111/255, blue: 103/255)` |
| 深色品牌底 | `#124940` | 主摘要卡與圖示背景 |
| 頁面背景 | `--page-bg: #F7F8F4` | grouped content 背景 |
| 主要文字 | `--text-color: #19332F` | 主要標題與金額 |
| 次要文字 | `--light-text-color: #647570` | 說明、輔助資訊 |
| 邊框 | `--border-color: #E5E9E3` | 卡片與輸入欄分隔 |
| 危險動作 | `--danger-color: #BB514C` | 刪除、錯誤 |
| 需要注意 | `--warning-color: #A86B32` | 提醒，不代表支出 |
| 品牌點綴 | `#D8A46D` | 少量使用於圖示或重點 |

字體沿用系統字體與繁體中文 fallback。頁面標題約 28–34pt、正文 16pt、輔助文字 12–14pt；金額使用 tabular figures。卡片圓角 20–24pt，控制項 12–14pt。互動區至少 44×44pt。主要資訊不要只靠顏色區分。

## 動態與狀態

- 切頁淡入與短距離位移約 360ms；按鈕回饋約 180ms；比例條約 320ms。
- 支援系統「減少動態效果」，停用非必要轉場。SwiftUI 應對應 `accessibilityReduceMotion`。
- Loading、empty、error 都要顯示清楚的原因與下一步；登入、記帳、旅行分攤不得靠動畫掩蓋等待或重送狀態。
- 底部導覽使用五個既有入口；帳號設定維持獨立入口。安全區與鍵盤遮擋需在裝置上確認。

## 已套用與待驗收

這一批已套用 Web 設計 token、首頁摘要卡、導覽、登入頁、PWA 圖示及基本互動動態。其他頁面先承接共用標題、主要按鈕與表面規則；複雜表單、旅行詳情、圖表和空狀態仍需逐頁檢查視覺一致性。

上架前另需確認：390/430/768px 主要流程、真實資料長金額與長名稱、VoiceOver、Dynamic Type、色彩對比、深色模式決策、登入與 session lifecycle、正式 iOS 功能及 TestFlight。Web build/lint 或本文件都不代表 iOS 已可上架。iOS 功能範圍仍依 `docs/product-roadmap.md` 的 M6A–M6C 門檻。

PWA 圖示來源為 `frontend/public/nomica-mark.svg`；macOS 可在 `frontend` 執行 `swift scripts/generate_app_icons.swift public` 產生 PNG，再用 `sips -s format ico public/favicon.png --out public/favicon.ico` 更新 ICO。
