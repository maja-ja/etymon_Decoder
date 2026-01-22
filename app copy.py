import streamlit as st
import json
import os
import random
import pandas as pd

# ==========================================
# 1. 核心配置與雲端同步
# ==========================================
SHEET_ID = '1W1ADPyf5gtGdpIEwkxBEsaJ0bksYldf4AugoXnq6Zvg'
GSHEET_URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv'
DB_FILE = 'etymon_database.json'
PENDING_FILE = 'pending_data.json'

def load_db():
    """從 Google Sheets 讀取表格並轉換為結構化數據"""
    try:
        df = pd.read_csv(GSHEET_URL)
        if df.empty:
            return []
        
        # 統一欄位名稱
        df.columns = [c.strip().lower() for c in df.columns]
        
        structured_data = []
        # 按分類分組
        for cat_name, cat_group in df.groupby('category'):
            root_groups = []
            # 按字根與意義分組
            for (roots, meaning), group_df in cat_group.groupby(['roots', 'meaning']):
                vocabulary = []
                for _, row in group_df.iterrows():
                    vocabulary.append({
                        "word": str(row['word']),
                        "breakdown": str(row['breakdown']),
                        "definition": str(row['definition'])
                    })
                root_groups.append({
                    "roots": [r.strip() for r in str(roots).split('/')],
                    "meaning": str(meaning),
                    "vocabulary": vocabulary
                })
            structured_data.append({
                "category": str(cat_name),
                "root_groups": root_groups
            })
        return structured_data
    except Exception as e:
        # 如果雲端失敗，嘗試讀取本地備份
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

def get_stats(data):
    """計算分類數與單字總量"""
    if not data: return 0, 0
    total_cats = len(data)
    total_words = sum(len(g.get('vocabulary', [])) for cat in data for g in cat.get('root_groups', []))
    return total_cats, total_words

def merge_logic(pending_data):
    """將 Pending 資料併入主資料庫並存為本地 JSON"""
    try:
        main_db = load_db()
        pending_list = [pending_data] if isinstance(pending_data, dict) else pending_data
        added_words = 0

        for new_cat in pending_list:
            cat_name = new_cat.get("category", "").strip()
            target_cat = next((c for c in main_db if c["category"] == cat_name), None)
            if not target_cat:
                main_db.append(new_cat)
            else:
                for new_group in new_cat.get("root_groups", []):
                    new_roots = set(new_group.get("roots", []))
                    target_group = next((g for g in target_cat.get("root_groups", []) if set(g.get("roots", [])) == new_roots), None)
                    if not target_group:
                        target_cat["root_groups"].append(new_group)
                    else:
                        existing = {v["word"].lower().strip() for v in target_group.get("vocabulary", [])}
                        for v in new_group.get("vocabulary", []):
                            if v["word"].lower().strip() not in existing:
                                target_group["vocabulary"].append(v)
                                added_words += 1
        
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(main_db, f, ensure_ascii=False, indent=2)
        return True, "合併完成"
    except Exception as e:
        return False, str(e)

# ==========================================
# 2. UI 頁面組件
# ==========================================

def ui_admin_page():
    st.title("管理區")
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False

    if not st.session_state.admin_authenticated:
        pwd = st.text_input("管理員密碼", type="password")
        if st.button("登入") and pwd == "8787":
            st.session_state.admin_authenticated = True
            st.rerun()
        return

    data = load_db()
    c_count, w_count = get_stats(data)
    st.metric("當前資料庫單字量", w_count)

    if st.button("🚀 執行 Pending 合併"):
        if os.path.exists(PENDING_FILE):
            with open(PENDING_FILE, 'r', encoding='utf-8') as f:
                new_data = json.load(f)
            success, msg = merge_logic(new_data)
            if success: st.success(msg); st.rerun()
        else: st.error("找不到檔案")

    st.subheader("☁️ 雲端存檔 (請下載後貼入 Google Sheets)")
    flat_list = []
    for cat in data:
        for group in cat.get('root_groups', []):
            for v in group.get('vocabulary', []):
                flat_list.append({
                    "category": cat['category'], "roots": "/".join(group['roots']),
                    "meaning": group['meaning'], "word": v['word'],
                    "breakdown": v['breakdown'], "definition": v['definition']
                })
    if flat_list:
        df_export = pd.DataFrame(flat_list)
        st.dataframe(df_export)
        csv = df_export.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載最新的單字表 (CSV)", csv, "words.csv", "text/csv")

def ui_medical_page(med_data):
    st.title("醫學區")
    for cat in med_data:
        for group in cat.get('root_groups', []):
            label = f"{' / '.join(group['roots'])} → {group['meaning']}"
            with st.expander(label):
                cols = st.columns(2)
                for i, v in enumerate(group.get('vocabulary', [])):
                    with cols[i % 2]:
                        st.markdown(f"**{v['word']}** \n`{v['breakdown']}`  \n{v['definition']}")

def ui_search_page(data, selected_cat):
    st.title("字根區")
    relevant = data if selected_cat == "全部顯示" else [c for c in data if c['category'] == selected_cat]
    query = st.text_input("搜尋單字...")
    for cat in relevant:
        for group in cat.get('root_groups', []):
            matched = [v for v in group['vocabulary'] if query.lower() in v['word'].lower()] if query else group['vocabulary']
            if matched:
                with st.expander(f"{'/'.join(group['roots'])} ({group['meaning']})"):
                    for v in matched:
                        st.write(f"**{v['word']}**: {v['definition']} (`{v['breakdown']}`)")

def ui_quiz_page(data):
    st.title("學習區")
    if 'flash_q' not in st.session_state:
        all_words = [{**v, "cat": c['category']} for c in data for g in c.get('root_groups', []) for v in g.get('vocabulary', [])]
        if not all_words: st.warning("目前無單字"); return
        st.session_state.flash_q = random.choice(all_words)
        st.session_state.flipped = False

    q = st.session_state.flash_q
    st.markdown(f"### {q['word']}")
    if st.button("查看答案"): st.session_state.flipped = True
    if st.session_state.get('flipped'):
        st.info(f"{q['breakdown']} - {q['definition']}")
    if st.button("下一題"):
        del st.session_state.flash_q
        st.rerun()

# ==========================================
# 3. 主程序入口
# ==========================================
def main():
    st.set_page_config(page_title="Etymon", layout="wide")
    data = load_db()
    st.sidebar.title("Etymon")
    menu = st.sidebar.radio("導航", ["字根區", "學習區", "醫學區", "管理區"])
    
    _, w = get_stats(data)
    st.sidebar.metric("總單字量", w)

    if menu == "管理後台": ui_admin_page()
    elif menu == "字根導覽":
        cats = ["全部顯示"] + sorted(list(set(c['category'] for c in data)))
        ui_search_page(data, st.sidebar.selectbox("分類", cats))
    elif menu == "記憶卡片": ui_quiz_page(data)
    elif menu == "醫學專區":
        med = [c for c in data if "醫學" in c['category']]
        ui_medical_page(med) if med else st.info("尚無醫學數據")

if __name__ == "__main__":
    main()
