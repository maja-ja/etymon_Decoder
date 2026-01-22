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
    try:
        df = pd.read_csv(GSHEET_URL)
        if df.empty: return []
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
            structured_data.append({"category": str(cat_name), "root_groups": root_groups})
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(structured_data, f, ensure_ascii=False, indent=2)
        return structured_data
    except Exception:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        return []

def get_stats(data):
    if not data: return 0, 0
    total_cats = len(data)
    total_words = sum(len(g.get('vocabulary', [])) for cat in data for g in cat.get('root_groups', []))
    return total_cats, total_words

# ==========================================
# 2. 通用與專業區域組件
# ==========================================

def ui_domain_page(domain_data, title, theme_color, bg_color):
    """通用專業區域：醫學、法律、AI、高中均可共用"""
    st.title(title)
    if not domain_data:
        st.info(f"💡 目前資料庫中尚未建立相關分類。")
        return

    # 提取所有字根組合
    root_map = {}
    for cat in domain_data:
        for group in cat.get('root_groups', []):
            label = f"{'/'.join(group['roots'])} ({group['meaning']})"
            if label not in root_map: root_map[label] = group
    
    selected_label = st.selectbox("🎯 選擇要複習的字根", sorted(root_map.keys()), key=title)
    
    if selected_label:
        group = root_map[selected_label]
        st.markdown(f"### 核心內容：{selected_label}")
        for v in group.get('vocabulary', []):
            st.markdown(f"""
                <div style="border: 2px solid #eee; padding: 20px; border-radius: 15px; margin-bottom: 15px; background-color: white; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);">
                    <div style="font-size: 2.2em; font-weight: bold; color: {theme_color};">{v['word']}</div>
                    <div style="margin: 10px 0;">
                        <span style="font-size: 1.1em; color: #666;">構造拆解：</span>
                        <span style="font-size: 1.6em; color: #D32F2F; font-family: monospace; background: {bg_color}; padding: 2px 10px; border-radius: 5px;">{v['breakdown']}</span>
                    </div>
                    <div style="font-size: 1.3em; color: #333;"><b>中文定義：</b> {v['definition']}</div>
                </div>
            """, unsafe_allow_html=True)
def ui_quiz_page(data):
    st.title("學習區 (Flashcards)")
    
    # 1. 建立一個帶有數量的選單列表 (優化顯示)
    cat_options_map = {} # 用來對應「顯示名稱」與「原始名稱」
    cat_options_list = ["全部練習"]
    
    for c in data:
        w_count = sum(len(g['vocabulary']) for g in c['root_groups'])
        display_name = f"{c['category']} ({w_count} 字)"
        cat_options_list.append(display_name)
        cat_options_map[display_name] = c['category']
    
    # 2. 只有一個 selectbox，並從 map 中還原原始 category 名稱
    selected_raw = st.selectbox("選擇練習範圍", sorted(cat_options_list))
    selected_cat = cat_options_map.get(selected_raw, "全部練習")

    # 3. 切換分類時重置題目
    if st.session_state.get('last_quiz_cat') != selected_cat:
        st.session_state.last_quiz_cat = selected_cat
        if 'flash_q' in st.session_state: 
            del st.session_state.flash_q
        st.rerun()

    # 4. 抽題邏輯
    if 'flash_q' not in st.session_state:
        if selected_cat == "全部練習":
            pool = [{**v, "cat": c['category']} for c in data for g in c['root_groups'] for v in g['vocabulary']]
        else:
            pool = [{**v, "cat": c['category']} for c in data if c['category'] == selected_cat for g in c['root_groups'] for v in g['vocabulary']]
        
        if not pool: 
            st.warning("此範圍目前沒有單字數據。")
            return
            
        st.session_state.flash_q = random.choice(pool)
        st.session_state.flipped = False

    # 5. UI 顯示卡片
    q = st.session_state.flash_q
    st.markdown(f"""
        <div style="text-align: center; padding: 50px; border: 3px solid #eee; border-radius: 25px; background: #fdfdfd; margin-bottom: 20px;">
            <p style="color: #999; font-size: 1.2em;">[ {q['cat']} ]</p>
            <h1 style="font-size: 4.5em; margin: 0; color: #1E88E5;">{q['word']}</h1>
        </div>
    """, unsafe_allow_html=True)

    # 6. 按鈕控制
    col1, col2 = st.columns(2)
    with col1:
        if st.button("查看答案", use_container_width=True): 
            st.session_state.flipped = True
    with col2:
        if st.button("下一題", use_container_width=True): 
            if 'flash_q' in st.session_state: 
                del st.session_state.flash_q
            st.rerun()

    # 7. 顯示答案
    if st.session_state.get('flipped'):
        st.markdown(f"""
            <div style="background-color: #E3F2FD; padding: 25px; border-radius: 15px; margin-top: 20px; border-left: 10px solid #1E88E5;">
                <p style="font-size: 2em; margin-bottom: 10px;"><b>拆解：</b> <span style="color: #D32F2F;">{q['breakdown']}</span></p>
                <p style="font-size: 1.5em;"><b>釋義：</b> {q['definition']}</p>
            </div>
        """, unsafe_allow_html=True)
def ui_search_page(data, selected_cat):
    st.title("搜尋與瀏覽")
    relevant = data if selected_cat == "全部顯示" else [c for c in data if c['category'] == selected_cat]
    query = st.text_input("搜尋單字或字根...").strip().lower()
    for cat in relevant:
        for group in cat.get('root_groups', []):
            matched = [v for v in group['vocabulary'] if query in v['word'].lower() or any(query in r.lower() for r in group['roots'])]
            if matched:
                with st.expander(f"{'/'.join(group['roots'])} ({group['meaning']})", expanded=bool(query)):
                    for v in matched:
                        st.markdown(f"**{v['word']}** [{v['breakdown']}]: {v['definition']}")

def ui_admin_page(data):
    st.title("管理區")
    if not st.session_state.get('admin_auth'):
        if st.text_input("密碼", type="password") == "8787": st.session_state.admin_auth = True; st.rerun()
        return
    st.metric("資料庫總量", f"{get_stats(data)[1]} 單字")
    if st.button("手動備份 CSV"):
        flat = [{"category": c['category'], "roots": "/".join(g['roots']), "meaning": g['meaning'], **v} for c in data for g in c['root_groups'] for v in g['vocabulary']]
        st.download_button("下載 CSV", pd.DataFrame(flat).to_csv(index=False).encode('utf-8-sig'), "backup.csv")

# ==========================================
# 3. 主程序入口
# ==========================================
def main():
    st.set_page_config(page_title="Etymon Decoder", layout="wide")
    data = load_db()
    
    # 1. 側邊欄標題
    st.sidebar.title("tymon Decoder")
    
    # 2. 導覽選單
    menu = st.sidebar.radio("導航", ["字根區", "學習區", "高中 7000 區", "醫學區", "法律區", "人工智慧區", "心理與社會區", "生物與自然區", "管理區"])
    
    st.sidebar.divider()
    
    # 3. 強制刷新按鈕
    if st.sidebar.button("強制刷新雲端數據", use_container_width=True): 
        st.cache_data.clear()
        st.rerun()
    
    # 4. 在刷新按鈕下方顯示單字總量 (使用大字體樣式)
    _, total_words = get_stats(data)
    st.sidebar.markdown(f"""
        <div style="text-align: center; padding: 10px; background-color: #f0f2f6; border-radius: 10px; margin-top: 10px;">
            <p style="margin: 0; font-size: 0.9em; color: #000;">資料庫總計</p>
            <p style="margin: 0; font-size: 1.8em; font-weight: bold; color: #000;">{total_words} <span style="font-size: 0.5em;">Words</span></p>
        </div>
    """, unsafe_allow_html=True)

    # --- 以下為各分頁呼叫邏輯 (維持不變) ---
    if menu == "字根區":
        cats = ["全部顯示"] + sorted(list(set(c['category'] for c in data)))
        ui_search_page(data, st.sidebar.selectbox("分類篩選", cats))
    elif menu == "學習區":
        ui_quiz_page(data)
    elif menu == "高中 7000 區":
        hs = [c for c in data if any(k in c['category'] for k in ["高中", "7000"])]
        count = sum(len(g['vocabulary']) for c in hs for g in c['root_groups'])
        ui_domain_page(hs, f"高中核心區 ({count} 字)", "#2E7D32", "#E8F5E9")
    elif menu == "醫學區":
        med = [c for c in data if "醫學" in c['category']]
        count = sum(len(g['vocabulary']) for c in med for g in c['root_groups'])
        ui_domain_page(med, f"醫學專業區 ({count} 字)", "#C62828", "#FFEBEE")
    elif menu == "法律區":
        law = [c for c in data if "法律" in c['category']]
        count = sum(len(g['vocabulary']) for c in law for g in c['root_groups'])
        ui_domain_page(law, f"法律術語區 ({count} 字)", "#4527A0", "#EDE7F6")
    elif menu == "人工智慧區":
        ai = [c for c in data if "人工智慧" in c['category'] or "AI" in c['category']]
        count = sum(len(g['vocabulary']) for c in ai for g in c['root_groups'])
        ui_domain_page(ai, f"AI 技術區 ({count} 字)", "#1565C0", "#E3F2FD")
    elif menu == "心理與社會區":
        psy = [c for c in data if any(k in c['category'] for k in ["心理", "社會", "Psych", "Soc"])]
        count = sum(len(g['vocabulary']) for c in psy for g in c['root_groups'])
        ui_domain_page(psy, f"🧠 心理與社會科學 ({count} 字)", "#AD1457", "#FCE4EC") # 桃紅色系
        
    elif menu == "生物與自然區":
        bio = [c for c in data if any(k in c['category'] for k in ["生物", "自然", "科學", "Bio", "Sci"])]
        count = sum(len(g['vocabulary']) for c in bio for g in c['root_groups'])
        ui_domain_page(bio, f"🌿 生物與自然科學 ({count} 字)", "#2E7D32", "#E8F5E9") # 深綠色系
if __name__ == "__main__":
    main()
