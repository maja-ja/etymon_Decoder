# Etymon Decoder - Project Documentation

Etymon Decoder is an English etymology learning tool built with **Streamlit**. The project core utilizes a **Google Sheets Cloud Sync** mechanism, supplemented by an automated localization backup logic, providing users with a seamless and stable root-learning experience.

## Core Architecture & Logic

### 1. Cloud-First Sync Logic

The application no longer relies on a static local database. Instead, it operates through the following workflow:

* **Real-time Fetching**: Upon startup, the app uses `pandas` to connect to the Google Sheets API (via CSV endpoint) to pull the latest vocabulary list directly from the cloud.
* **Local Caching & Backup**: Once successfully read, the app automatically generates/updates `etymon_database.json` as a backup cache. If the cloud connection fails (e.g., offline), the system seamlessly switches to this backup file.
* **Data Structuring**: Flat spreadsheet rows are transformed into a nested hierarchy of "Category > Root Group > Vocabulary" for efficient searching and display.

### 2. Data Hierarchy Design

Data is organized within the program using the following logic:

* **Category**: The highest level, such as "High School Vocabulary" or "Medical Terminology."
* **Root Group**: Clusters of synonymous roots and their core meaning (e.g., `vis/vid` representing "to see").
* **Vocabulary**: Specific word entries, including structural breakdown and definitions.

---

## Functional Modules

### Root Zone (Search Engine)

* **Search Logic**: Supports filtering by category and real-time keyword retrieval for both words and roots.
* **UI Optimization**: Uses `st.expander` to collapse detailed information, maintaining a clean and professional interface.

### Learning Zone (Flashcard Logic)

* **Randomized Algorithm**: Randomly samples words from the current database for testing.
* **State Management**: Utilizes `st.session_state` to record questions and card flip states, preventing data loss when the page is refreshed.

### Medical Zone (Specialty Content)

* **Automatic Routing**: The system automatically scans category names. Any category containing the keyword "Medical" is independently displayed in this professional section with a card-based layout.

### Admin Zone (Management Logic)

* **Data Merging**: Provides a one-click merge feature to integrate external `pending_data.json` into the main database.
* **Backup Export**: Supports restoring the current database into a flat CSV format, allowing administrators to download and update the master Google Sheet.

---

## Technical Stack

* **Frontend Framework**: Streamlit
* **Data Handling**: Pandas, JSON
* **Cloud Integration**: Google Sheets API (via CSV export)
* **Programming Language**: Python 3.13
