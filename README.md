# 🧠 Etymon Decoder 程式邏輯說明（繁中）

本專案是一個基於 **Streamlit** 開發的英語字根學習工具，結合了 **Google Sheets 雲端同步** 與 **在地化資料管理** 的雙軌邏輯。

## 🏗️ 核心架構邏輯

### 1. 資料雙軌同步 (Sync Logic)

程式採用「雲端為主，在地為輔」的設計：

* **雲端讀取**：啟動時透過 `pandas` 直接讀取公開的 Google Sheets CSV 連結。
* **在地備援**：若網路斷線或雲端讀取失敗，程式會自動切換讀取本地的 `etymon_database.json`。
* **格式轉換**：將扁平的試算表表格（Table）轉化為巢狀的 JSON 結構，以對應「分類 > 字根組 > 單字」的層級關係。

### 2. 資料層級設計 (Data Hierarchy)

資料在程式內部以以下邏輯組織：

* **Category (分類)**：如「高中常見字根」、「專業醫學術語」。
* **Root Group (字根組)**：包含同義的多個字根（如 `vis/vid`）及其核心意義。
* **Vocabulary (單字庫)**：包含單字、拆解（Breakdown）及釋義。

### 3. 功能模組邏輯

#### 🔍 字根導覽 (Search Engine)

* **篩選邏輯**：支援按「分類」過濾，並提供即時關鍵字檢索。
* **展示邏輯**：使用 `st.expander` 摺疊顯示，保持介面簡潔。

#### 🧠 學習區 (Flashcard Logic)

* **隨機算法**：從當前所有資料中隨機抽樣（Random Sampling）一個單字。
* **狀態管理**：利用 `st.session_state` 紀錄目前抽到的題目與卡片翻轉狀態（正面/背面），確保頁面重整時題目不會消失。

#### 🏥 醫學專區 (Niche Filtering)

* **自動分流**：程式會自動篩選分類名稱中包含「醫學」關鍵字的資料夾，獨立展示在專業區塊。

#### 🛠️ 管理後台 (Admin & Merge Logic)

* **身份驗證**：簡單的密碼雜湊與 Session 鎖定。
* **資料合併 (Merge)**：提供「一鍵合併」功能，將 `pending_data.json`（外部匯入的新單字）併入主資料庫，並具備**重複單字過濾**機制。
* **逆向導出**：支援將 JSON 結構重新攤平成 CSV 表格，方便管理員下載並更新回 Google Sheets。
# -----------
# 🧠 Etymon Decoder 程序逻辑说明 (简体中文)

本项目是一个基于 **Streamlit** 开发的英语词根学习工具，采用 **Google Sheets 云端同步** 与 **本地化数据管理** 的双轨逻辑。

### 🏗️ 核心架构逻辑

#### 1. 数据双轨同步 (Sync Logic)

程序采用“云端为主，本地为辅”的设计：

* **云端读取**：启动时通过 `pandas` 直接读取公开的 Google Sheets CSV 链接。
* **本地备援**：若网络故障或云端读取失败，程序会自动切换读取本地的 `etymon_database.json`。
* **格式转换**：将扁平的电子表格（Table）转化为嵌套的 JSON 结构，以对应“分类 > 词根组 > 单词”的层级关系。

#### 2. 数据层级设计 (Data Hierarchy)

数据在程序内部通过以下逻辑组织：

* **Category (分类)**：如“高中常见词根”、“专业医学术语”。
* **Root Group (词根组)**：包含同义的多个词根（如 `vis/vid`）及其核心意义。
* **Vocabulary (单词库)**：包含单词、拆解（Breakdown）及释义。

#### 3. 功能模块逻辑

* **🔍 词根导览 (Search Engine)**：支持按分类过滤，并利用即时关键词检索功能。使用 `st.expander` 折叠显示，保持界面简洁。
* **🧠 学习区 (Flashcard Logic)**：从当前数据中随机抽样（Random Sampling）单词。利用 `st.session_state` 记录题目与卡片翻转状态，确保页面刷新时进度不丢失。
* **🏥 医学专区 (Niche Filtering)**：程序自动筛选分类名称中包含“医学”关键字的数据，进行独立展示。
* **🛠️ 管理后台 (Admin & Merge Logic)**：提供“一键合并”功能，将 `pending_data.json` 里的新数据并入主数据库，并具备**重复单词过滤**机制。

---
# 🧠 Etymon Decoder – Logic & Architecture (English Version)

Etymon Decoder is an English etymology learning tool built with **Streamlit**. It features a hybrid data architecture combining **Google Sheets Cloud Sync** with **Local JSON management**.

### 🏗️ Core Logic Flow

#### 1. Dual-Track Data Sync

The program follows a "Cloud-First, Local-Backup" strategy:

* **Cloud Fetching**: Upon startup, the app uses `pandas` to fetch live data from a public Google Sheets CSV export link.
* **Local Fallback**: If the network is unavailable or the cloud link fails, the system automatically switches to the local `etymon_database.json`.
* **Data Transformation**: It transforms flat spreadsheet rows into a nested JSON object to handle the "Category > Root Group > Vocabulary" hierarchy.

#### 2. Data Hierarchy Design

Data is structured within the application as follows:

* **Category**: High-level grouping (e.g., "High School Vocabulary").
* **Root Group**: Clusters of synonymous roots (e.g., `vis / vid`) and their core meaning (e.g., "to see").
* **Vocabulary**: Individual words including their structural breakdown and definition.

#### 3. Functional Modules

* **🔍 Root Explorer (Search Engine)**: Supports filtering by Category and real-time keyword searching. Uses `st.expander` to keep the interface clean while browsing large datasets.
* **🧠 Learning Center (Flashcard Logic)**: Uses randomized sampling to present words. Utilizes `st.session_state` to track the current card and its "flipped" status, preventing data loss during page re-runs.
* **🏥 Medical Specialty Zone**: The system automatically filters any category containing the keyword "Medical" and displays it in a dedicated professional layout.
* **🛠️ Admin & Merge Logic**: Features a "One-Click Merge" function that integrates new words from `pending_data.json` into the main database with a **duplicate-check mechanism**.

---

### 🛠️ Technical Stack

* **Frontend**: Streamlit
* **Data Handling**: Pandas, JSON
* **Cloud Integration**: Google Sheets API (via CSV endpoint)
* **Language**: Python 3.13
