import streamlit as st
import json
import os
import random

# ==========================================
# 1. 核心配置與數據處理
# ==========================================
DB_FILE = 'etymon_database.json'
PENDING_FILE = 'pending_data.json'

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            try: return json.load(f)
            except: return []
    return []

def get_stats(data):
    total_cats = len(data)
    total_words = sum(len(g.get('vocabulary', [])) for cat in data for g in cat.get('root_groups', []))
    return total_cats, total_words

def merge_logic(pending_data):
    try:
        main_db = load_db()
        pending_list = [pending_data] if isinstance(pending_data, dict) else pending_data
        added_cats, added_groups, added_words = 0, 0, 0

        for new_cat in pending_list:
            cat_name = new_cat.get("category", "").strip()
            if not cat_name: continue
            
            target_cat = next((c for c in main_db if c["category"] == cat_name), None)
            
            if not target_cat:
                main_db.append(new_cat)
                added_cats += 1
                for g in new_cat.get("root_groups", []):
                    added_words += len(g.get("vocabulary", []))
            else:
                for new_group in new_cat.get("root_groups", []):
                    new_roots = set(new_group.get("roots", []))
                    target_group = next((g for g in target_cat.get("root_groups", []) 
                                       if set(g.get("roots", [])) == new_roots), None)
                    
                    if not target_group:
                        target_cat["root_groups"].append(new_group)
                        added_groups += 1
                        added_words += len(new_group.get("vocabulary", []))
                    else:
                        existing_words = {v["word"].lower().strip() for v in target_group.get("vocabulary", [])}
                        for v in new_group.get("vocabulary", []):
                            word_clean = v["word"].lower().strip()
                            if word_clean not in existing_words:
                                target_group["vocabulary"].append(v)
                                existing_words.add(word_clean)
                                added_words += 1
        
        if added_cats == 0 and added_groups == 0 and added_words == 0:
            return False, "資料庫中已存在相同的資料。"

        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(main_db, f, ensure_ascii=False, indent=2)
        return True, f"新增了 {added_cats} 分類, {added_groups} 字根組, {added_words} 單字。"
    except Exception as e:
        return False, f"錯誤: {str(e)}"

# ==========================================
# 2. UI 頁面組件
# ==========================================

def ui_admin_page():
    st.title("數據管理後台")
    ADMIN_PASSWORD = "8787"
    
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False

    if not st.session_state.admin_authenticated:
        pwd_input = st.text_input("請輸入管理員密碼", type="password")
        if st.button("登入"):
            if pwd_input == ADMIN_PASSWORD:
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("密碼錯誤")
        return

    # 管理介面
    if st.button("登出管理台"):
        st.session_state.admin_authenticated = False
        st.rerun()

    tab1, tab2 = st.tabs(["方案 A：一鍵合併檔案", "方案 B：手動貼上 JSON"])

    with tab1:
        st.subheader("從 `pending_data.json` 合併")
        if st.button("執行一鍵合併", use_container_width=True):
            if not os.path.exists(PENDING_FILE):
                st.error(f"找不到 `{PENDING_FILE}`")
            else:
                try:
                    with open(PENDING_FILE, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                    if content:
                        success, msg = merge_logic(content)
                        if success:
                            with open(PENDING_FILE, 'w', encoding='utf-8') as f:
                                json.dump([], f)
                            st.success(msg)
                            st.cache_data.clear()
                        else:
                            st.warning(msg)
                except Exception as e:
                    st.error(f"處理失敗: {e}")

    with tab2:
        json_input = st.text_area("在此貼上 JSON 內容", height=200)
        if st.button("執行手動合併"):
            try:
                data = json.loads(json_input)
                success, msg = merge_logic(data)
                if success:
                    st.success(msg)
                    st.cache_data.clear()
            except:
                st.error("JSON 格式無效")

def ui_medical_page(med_data):
    st.title("醫學術語專業區")
    st.info("醫學術語通常由字根(Root)、前綴(Prefix)與後綴(Suffix)組成。")
    
    # 插入醫學解剖輔助圖示
    st.markdown("---")
    

    all_med_roots = []
    for cat in med_data:
        for group in cat['root_groups']:
            all_med_roots.append(f"{' / '.join(group['roots'])} → {group['meaning']}")
    
    selected_med = st.selectbox("快速定位醫學字根", all_med_roots)
    
    for cat in med_data:
        for group in cat['root_groups']:
            label = f"{' / '.join(group['roots'])} → {group['meaning']}"
            with st.expander(f"核心字根：{label}", expanded=(label == selected_med)):
                cols = st.columns(2)
                for i, v in enumerate(group['vocabulary']):
                    with cols[i % 2]:
                        st.markdown(f"""
                        <div style="padding:15px; border-radius:10px; border-left:5px solid #ff4b4b; background-color:#f0f2f6; margin-bottom:10px;">
                            <h4 style="margin:0; color:#1f77b4;">{v['word']}</h4>
                            <p style="margin:5px 0; font-size:0.9rem;"><b>結構：</b><code>{v['breakdown']}</code></p>
                            <p style="margin:0; font-weight:bold;">釋義：{v['definition']}</p>
                        </div>
                        """, unsafe_allow_html=True)

def ui_search_page(data, selected_cat):
    st.title("字根導覽")
    relevant_cats = data if selected_cat == "全部顯示" else [c for c in data if c['category'] == selected_cat]
    
    root_options = []
    root_to_group = {}
    for cat in relevant_cats:
        for group in cat.get('root_groups', []):
            label = f"{' / '.join(group['roots'])} ({group['meaning']})"
            root_options.append(label)
            root_to_group[label] = (cat['category'], group)
    
    selected_root_label = st.selectbox("選擇字根組", ["顯示全部"] + root_options)
    st.divider()

    if selected_root_label == "顯示全部":
        query = st.text_input("檢索單字", placeholder="輸入單字搜尋...").lower().strip()
        for label in root_options:
            cat_name, group = root_to_group[label]
            matched_v = [v for v in group['vocabulary'] if query in v['word'].lower()] if query else group['vocabulary']
            if matched_v:
                st.markdown(f"#### {label}")
                for v in matched_v:
                    with st.expander(f"{v['word']}", expanded=bool(query)):
                        st.write(f"結構: `{v['breakdown']}`")
                        st.write(f"釋義: {v['definition']}")
    else:
        cat_name, group = root_to_group[selected_root_label]
        st.caption(f"分類：{cat_name}")
        for v in group['vocabulary']:
            with st.expander(f"{v['word']}", expanded=True):
                st.write(f"結構: `{v['breakdown']}`")
                st.write(f"釋義: {v['definition']}")

def ui_quiz_page(data):
    if 'failed_words' not in st.session_state: st.session_state.failed_words = set()
    if 'quiz_active' not in st.session_state: st.session_state.quiz_active = False

    if not st.session_state.quiz_active:
        st.title("記憶卡片")
        categories = ["全部隨機"] + sorted([c['category'] for c in data])
        selected_quiz_cat = st.selectbox("選擇練習範圍", categories)
        if st.button("開始練習", use_container_width=True):
            st.session_state.selected_quiz_cat = selected_quiz_cat
            st.session_state.quiz_active = True
            if 'flash_q' in st.session_state: del st.session_state.flash_q
            st.rerun()
        return

    # 練習介面
    col_t1, col_t2 = st.columns([4, 1])
    col_t1.caption(f"範圍: {st.session_state.selected_quiz_cat}")
    if col_t2.button("結束"):
        st.session_state.quiz_active = False
        st.rerun()

    relevant_data = data if st.session_state.selected_quiz_cat == "全部隨機" else [c for c in data if c['category'] == st.session_state.selected_quiz_cat]
    all_words = [{**v, "cat": cat['category']} for cat in relevant_data for group in cat.get('root_groups', []) for v in group.get('vocabulary', [])]

    if not all_words:
        st.warning("查無資料")
        st.session_state.quiz_active = False
        return

    if 'flash_q' not in st.session_state:
        st.session_state.flash_q = random.choice(all_words)
        st.session_state.is_flipped = False

    q = st.session_state.flash_q
    
    # 卡片 CSS
    st.markdown(f"""
    <div style="background:white; padding:40px; border-radius:20px; border:2px solid #f0f2f6; text-align:center; min-height:250px; box-shadow: 0 10px 20px rgba(0,0,0,0.05);">
        <small style="color:#888;">{q['cat'].upper()}</small>
        <h1 style="font-size:3.5rem; margin:20px 0;">{q['word']}</h1>
        {f'<hr><p style="font-size:1.2rem; color:#0366d6;"><code>{q["breakdown"]}</code></p><h3>{q["definition"]}</h3>' if st.session_state.is_flipped else '<p style="color:#ccc;">點擊下方按鈕查看答案</p>'}
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    if not st.session_state.is_flipped:
        if st.button("翻轉卡片", use_container_width=True, type="primary"):
            st.session_state.is_flipped = True
            st.rerun()
    else:
        c1, c2 = st.columns(2)
        if c1.button("下一題", use_container_width=True):
            if 'flash_q' in st.session_state: del st.session_state.flash_q
            st.rerun()
        if c2.button("標記陌生", use_container_width=True):
            st.session_state.failed_words.add(q['word'])
            if 'flash_q' in st.session_state: del st.session_state.flash_q
            st.rerun()

# ==========================================
# 3. 主程序入口
# ==========================================

def main():
    st.set_page_config(page_title="Etymon 智選", layout="wide")
    data = load_db()
    
    st.sidebar.title("Etymon")
    menu = st.sidebar.radio("功能導航", ["字根導覽", "記憶卡片", "醫學專區", "管理後台"])
    
    st.sidebar.divider()
    categories = ["全部顯示"] + sorted([c['category'] for c in data])
    selected_cat = st.sidebar.selectbox("全域過濾分類", categories)
    
    c_count, w_count = get_stats(data)
    st.sidebar.metric("目前分類", c_count)
    st.sidebar.metric("總單字量", w_count)

    if menu == "字根導覽":
        ui_search_page(data, selected_cat)
    elif menu == "記憶卡片":
        ui_quiz_page(data)
    elif menu == "醫學專區":
        med_data = [c for c in data if "醫學" in c['category']]
        if med_data: ui_medical_page(med_data)
        else: st.info("尚未導入醫學分類數據")
    elif menu == "管理後台":
        ui_admin_page()

if __name__ == "__main__":
    main()
