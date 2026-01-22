# Etymon Decoder 專案說明文件

這是一個基於 **Streamlit** 開發的英語字根學習工具。專案核心採用 **Google Sheets 雲端同步** 機制，並輔以自動化的在地化備援邏輯，為使用者提供流暢且穩定的字根學習體驗。

## 核心架構與邏輯

### 1. 雲端優先同步邏輯 (Cloud-First Sync)

* **即時讀取**：啟動時透過 `pandas` 串接 Google Sheets API (CSV 終端)，直接抓取雲端最新的單字表。
* **在地快取與備援**：成功讀取後會自動產生 `etymon_database.json` 作為備援快取。若雲端連結失效（如斷網），系統將無縫切換至備援檔案。
* **數據結構化**：將扁平的試算表列（Row）轉化為「分類 > 字根組 > 單字」的巢狀層級，以利於高效搜尋與展示。

### 2. 資料層級設計 (Data Hierarchy)

資料在程式內部以以下邏輯組織：

* **分類 (Category)**：最高層級，如「高中常見字根」、「醫學術語」。
* **字根組 (Root Group)**：包含多個同義字根及其核心意義（如 `vis/vid` 代表「看」）。
* **單字庫 (Vocabulary)**：具體的單字內容，包含字構拆解（Breakdown）與定義。

---

## 功能模組說明

### 字根區 (Search Engine)

* **檢索邏輯**：支援按分類篩選，並結合即時關鍵字檢索。
* **UI 優化**：使用 `st.expander` 摺疊顯示詳細資訊，保持介面簡潔。

### 學習區 (Flashcard Logic)

* **隨機演算法**：從當前資料庫中隨機抽樣單字進行測驗。
* **狀態管理**：利用 `st.session_state` 紀錄題目與卡片狀態，防止網頁重整時進度遺失。

### 醫學區 (Medical Specialty)

* **自動分流**：系統會自動掃描分類名稱，若包含「醫學」關鍵字，將獨立展示於此區域。

### 管理區 (Admin Logic)

* **數據合併**：提供一鍵合併功能，可將外部 `pending_data.json` 併入資料庫。
* **備份匯出**：支援將當前資料庫還原為 CSV，方便管理員下載後更新回 Google Sheets。

---

## 技術棧 (Technical Stack)

* **前端框架**: Streamlit
* **數據處理**: Pandas, JSON
* **雲端驅動**: Google Sheets API (via CSV export)
* **程式語言**: Python 3.13

---

## 📖 如何更新單字表？

1. **編輯雲端表格**：直接在指定的 Google Sheets 中新增單字。
2. **欄位規範**：請確保試算表具備以下小寫欄位名：`category`, `roots`, `meaning`, `word`, `breakdown`, `definition`。
3. **強制刷新**：在網頁側邊欄點擊「強制刷新雲端數據」即可看見更新成果。
