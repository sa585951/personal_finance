# 多使用者架構重構計畫 (Multi-User Refactoring Plan)

這份文件記錄了將個人記帳機器人升級為多使用者架構的完整待辦事項。

## 核心概念

為了讓每個使用者（家人、朋友）都擁有獨立的資料空間，我們需要在儲存使用者資料的每一張資料表中，新增一個 `user_id` 欄位。這個欄位將作為資料的「擁有者標籤」，確保任何操作都只會影響到當前使用者的資料。

---

## 🚀 行動計畫 (To-Do List)

### ☐ 第一步：修改資料庫 Schema (`models/schema.py`)
- [ ] **`assets_table`**: 新增 `user_id` 欄位 (`Column('user_id', String(255), nullable=False, index=True)`)
- [ ] **`transactions_table`**: 新增 `user_id` 欄位 (`Column('user_id', String(255), nullable=False, index=True)`)
- [ ] **`goals_table`**: 新增 `user_id` 欄位 (`Column('user_id', String(255), nullable=False, index=True)`)

---

### ☐ 第二步：升級所有 Manager (資料專家)
**目標**：讓所有 Manager 的方法都學會按 `user_id` 操作資料。

- **`models/asset_manager.py`**
    - [ ] 為所有公開方法 (public methods) 的第一個參數新增 `user_id`。
    - [ ] 在所有 `select`, `update`, `delete` 語句中，加入 `.where(assets_table.c.user_id == user_id)` 條件。
    - [ ] 在 `insert` 語句中，加入 `user_id` 的值。

- **`models/budget_manager.py`**
    - [ ] 為所有公開方法的第一個參數新增 `user_id`。
    - [ ] 在所有資料庫查詢中加入 `user_id` 過濾條件。

- **`models/goal_manager.py`**
    - [ ] 為所有公開方法的第一個參數新增 `user_id`。
    - [ ] 在所有資料庫查詢中加入 `user_id` 過濾條件。

---

### ☐ 第三步：串連 Handler 與 Manager
**目標**：讓 `Handler` (大腦) 在呼叫 `Manager` (資料專家) 時，把 `user_id` 傳遞下去。

- [ ] 檢查 `models/linebot/message_handler.py` 中所有對 Manager 的呼叫。
- [ ] 檢查所有 `models/linebot/flow_handlers/*.py` 檔案中對 Manager 的呼叫。
- [ ] 在上述呼叫中，將 `user_id` 作為第一個參數傳入。例如：`self.asset_manager.get_all_assets(user_id)`。

---

### ☐ 第四步：資料庫遷移
- [ ] **策略決定**: 選擇如何處理現有資料。
    - **建議選項**: 完成程式碼重構後，刪除舊的資料庫檔案/清空資料表，使用一個全新的、乾淨的資料庫開始。
    - **進階選項**: 編寫一個一次性腳本，將現有資料全部更新，為它們標上你自己的 `user_id`。
- [ ] **執行**: 根據所選策略，更新或重建資料庫。

---

## 檔案變動總結

### ✅ 幾乎不需修改的檔案
*   所有 `Theme` 檔案 (`operation_theme.py`, `statistics_theme.py`)
*   所有 `Parser` 檔案 (`parsers.py`, `message_parser.py`)
*   `UserStateManager`

### ⚠️ 需要「升級手術」的檔案
*   `models/schema.py`
*   `models/asset_manager.py`
*   `models/budget_manager.py`
*   `models/goal_manager.py`
*   `models/linebot/message_handler.py`
*   所有 `models/linebot/flow_handlers/` 下的檔案
