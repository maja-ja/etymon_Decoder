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

@st.cache_data(ttl=600)
def load_db():
    """從 Google Sheets 讀取表格並轉換為結構化數據"""
    try:
        df = pd.read_csv(GSHEET_URL)
        if df.empty:
            return []
        
        df.columns = [c.strip().lower() for c in df.columns]
        
        structured_data = []
        for cat_name, cat_group in df.groupby('category'):
            root_groups = []
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
        
        # 成功讀取後備份到本地
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(structured_data, f, ensure_ascii=False, indent=2)
            
        return structured_data
    except Exception as e:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

def get_stats(data):
    """計算分類數與單字總量"""
    if not data: return 0, 0
    total_cats = len(data)
    total_words = sum(len(g.get('vocabulary', [])) for cat in data for g in cat.get('root_groups', []))
    return total_cats, total_words

def merge_logic(pending_data):
    """將 Pending 資料併入資料庫並存為備份"""
    try:
        main_db = load_db()
        pending_list = [pending_data] if isinstance(pending_data, dict) else pending_data
        
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
        
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(main_db, f, ensure_ascii=False, indent=2)
        return True, "合併完成。請下載 CSV 並更新雲端試算表。"
    except Exception as e:
        return False, str(e)

# ==========================================
# 2. UI 頁面組件
# ==========================================
def ui_highschool_page(hs_data):
    st.title("高中 7000 單字區")
    
    if not hs_data:
        st.info("💡 目前資料庫中尚無標記為『高中』或『7000』的分類。")
        return

    # 1. 提取所有高中分類下的字根組合
    # 格式化為: "roots (meaning)"，方便使用者選擇
    root_options = []
    root_map = {} # 用來存放選單字串與實際資料的對應

    for cat in hs_data:
        for group in cat.get('root_groups', []):
            label = f"{'/'.join(group['roots'])} ({group['meaning']})"
            if label not in root_map:
                root_map[label] = group
                root_options.append(label)
    
    root_options.sort() # 按字母排序

    # 2. 讓使用者選擇字根
    selected_label = st.selectbox("🎯 選擇要複習的字根", root_options)
    
    if selected_label:
        selected_group = root_map[selected_label]
        
        # 顯示標題與視覺裝飾
        st.subheader(f"字根探索：{selected_label}")
        
        # 3. 呈現該字根下的所有單字
        # 使用欄位來呈現，讓畫面更活潑
        for v in selected_group.get('vocabulary', []):
            with st.container():
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.markdown(f"### **{v['word']}**")
                with col2:
                    st.markdown(f"**拆解：** `{v['breakdown']}`")
                    st.markdown(f"**中文定義：** {v['definition']}")
                st.divider()

        # 4. 額外的小提示
        st.caption(f"此字根收錄於：{', '.join(set(c['category'] for c in hs_data if selected_label in [f{'/'.join(g['roots'])} ({g['meaning']})' for g in c.get('root_groups', [])]))}")
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
    _, w_count = get_stats(data)
    st.metric("資料庫總量", f"{w_count} 單字")

    st.subheader("數據合併操作")
    if st.button("執行 Pending 合併"):
        if os.path.exists(PENDING_FILE):
            with open(PENDING_FILE, 'r', encoding='utf-8') as f:
                new_data = json.load(f)
            success, msg = merge_logic(new_data)
            if success: 
                st.success(msg)
                st.rerun()
        else:
            st.warning(f"找不到檔案 {PENDING_FILE}")

    st.divider()
    st.subheader("備份與匯出")
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
        st.dataframe(df_export, use_container_width=True)
        csv = df_export.to_csv(index=False).encode('utf-8-sig')
        st.download_button("下載備份 CSV", csv, "etymon_backup.csv", "text/csv")

def ui_medical_page(med_data):
    st.title("醫學區")
    for cat in med_data:
        st.caption(f"分類: {cat['category']}")
        for group in cat.get('root_groups', []):
            label = f"{' / '.join(group['roots'])} -> {group['meaning']}"
            with st.expander(label):
                cols = st.columns(2)
                for i, v in enumerate(group.get('vocabulary', [])):
                    with cols[i % 2]:
                        st.markdown(f"""
                        <div style="border:1px solid #ddd; padding:10px; border-radius:10px; margin-bottom:10px;">
                            <h4 style="margin:0;">{v['word']}</h4>
                            <p style="font-size:0.8em; color:#888;">拆解: {v['breakdown']}</p>
                            <p style="margin-top:5px;">{v['definition']}</p>
                        </div>
                        """, unsafe_allow_html=True)

def ui_search_page(data, selected_cat):
    st.title("字根區")
    relevant = data if selected_cat == "全部顯示" else [c for c in data if c['category'] == selected_cat]
    query = st.text_input("搜尋單字或字根...").strip().lower()
    
    for cat in relevant:
        for group in cat.get('root_groups', []):
            matched = []
            for v in group['vocabulary']:
                if query in v['word'].lower() or any(query in r.lower() for r in group['roots']):
                    matched.append(v)
            
            if matched:
                with st.expander(f"{'/'.join(group['roots'])} ({group['meaning']})", expanded=bool(query)):
                    for v in matched:
                        st.markdown(f"**{v['word']}**: {v['definition']}  \n結構: {v['breakdown']}")

def ui_quiz_page(data):
    st.title("學習區")
    
    # 1. 準備選單選項
    all_categories = sorted(list(set(c['category'] for c in data)))
    quiz_options = ["全部顯示"] + all_categories
    
    # 2. 在頁面上方加入分類選單
    selected_quiz_cat = st.selectbox("選擇練習範圍", quiz_options)
    
    # 3. 處理重置邏輯：如果分類改變了，就清空目前的題目
    if 'current_quiz_cat' not in st.session_state:
        st.session_state.current_quiz_cat = selected_quiz_cat
    
    if st.session_state.current_quiz_cat != selected_quiz_cat:
        st.session_state.current_quiz_cat = selected_quiz_cat
        if 'flash_q' in st.session_state:
            del st.session_state.flash_q
        st.rerun()

    # 4. 抽題邏輯
    if 'flash_q' not in st.session_state:
        # 根據選單篩選單字池
        if selected_quiz_cat == "全部顯示":
            all_words = [{**v, "cat": c['category']} for c in data for g in c.get('root_groups', []) for v in g.get('vocabulary', [])]
        else:
            all_words = [{**v, "cat": c['category']} for c in data if c['category'] == selected_quiz_cat 
                         for g in c.get('root_groups', []) for v in g.get('vocabulary', [])]
        
        if not all_words:
            st.warning(f"『{selected_quiz_cat}』分類中目前沒有單字數據。")
            return
        
        st.session_state.flash_q = random.choice(all_words)
        st.session_state.flipped = False

    q = st.session_state.flash_q
    
    # 5. UI 顯示
    st.markdown(f"""
    <div style="text-align: center; padding: 40px; border: 2px solid #ddd; border-radius: 20px; background-color: #f9f9f9; margin-bottom: 20px;">
        <p style="color: #666; font-weight: bold;">[ {q['cat']} ]</p>
        <h1 style="font-size: 4em; margin: 0; color: #1E88E5;">{q['word']}</h1>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("查看答案", use_container_width=True):
            st.session_state.flipped = True
    with col2:
        if st.button("下一題", use_container_width=True):
            if 'flash_q' in st.session_state:
                del st.session_state.flash_q
            st.rerun()

    # 6. 顯示答案
    if st.session_state.get('flipped'):
        st.markdown(f"""
        <div style="background-color: #e3f2fd; padding: 20px; border-radius: 15px; margin-top: 20px;">
            <p style="font-size: 1.2em;"><b>拆解：</b> {q['breakdown']}</p>
            <p style="font-size: 1.2em;"><b>釋義：</b> {q['definition']}</p>
        </div>
        """, unsafe_allow_html=True)
# ==========================================
# 3. 主程序入口
# ==========================================
def main():
    st.set_page_config(page_title="Etymon Decoder", layout="wide")
    data = load_db()
    
    st.sidebar.title("Etymon Decoder")
    # 在這裡新增 "高中 7000 區"
    menu = st.sidebar.radio("導航", ["字根區", "學習區", "高中 7000 區", "醫學區", "管理區"])
    
    _, w_count = get_stats(data)
    st.sidebar.divider()
    st.sidebar.metric("單字總量", w_count)
    
    if st.sidebar.button("強制刷新雲端數據"):
        st.cache_data.clear()
        st.rerun()

    if menu == "管理區":
        ui_admin_page()
    elif menu == "字根區":
        cats = ["全部顯示"] + sorted(list(set(c['category'] for c in data)))
        ui_search_page(data, st.sidebar.selectbox("篩選分類", cats))
    elif menu == "學習區":
        ui_quiz_page(data)
    elif menu == "高中 7000 區":
        # 篩選 category 包含 "高中" 或 "7000" 的資料
        hs_data = [c for c in data if any(k in c['category'] for k in ["高中", "7000"])]
        ui_highschool_page(hs_data)
    elif menu == "醫學區":
        med = [c for c in data if "醫學" in c['category']]
        if med:
            ui_medical_page(med)
        else:
            st.info("尚未包含醫學相關分類。")
if __name__ == "__main__":
    main()
