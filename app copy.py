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
    all_cats = sorted(list(set(c['category'] for c in data)))
    selected_cat = st.selectbox("選擇練習範圍", ["全部顯示"] + all_cats)

    # 切換分類時重置題目
    if st.session_state.get('last_quiz_cat') != selected_cat:
        st.session_state.last_quiz_cat = selected_cat
        if 'flash_q' in st.session_state: del st.session_state.flash_q

    if 'flash_q' not in st.session_state:
        if selected_cat == "全部顯示":
            pool = [{**v, "cat": c['category']} for c in data for g in c['root_groups'] for v in g['vocabulary']]
        else:
            pool = [{**v, "cat": c['category']} for c in data if c['category'] == selected_cat for g in c['root_groups'] for v in g['vocabulary']]
        
        if not pool: st.warning("此範圍無資料"); return
        st.session_state.flash_q = random.choice(pool)
        st.session_state.flipped = False

    q = st.session_state.flash_q
    st.markdown(f"""
        <div style="text-align: center; padding: 50px; border: 3px solid #eee; border-radius: 25px; background: #fdfdfd;">
            <p style="color: #999;">{q['cat']}</p>
            <h1 style="font-size: 4.5em; margin: 0; color: #1E88E5;">{q['word']}</h1>
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("查看答案", use_container_width=True, type="primary"): st.session_state.flipped = True
    with col2:
        if st.button("下一題", use_container_width=True): 
            if 'flash_q' in st.session_state: del st.session_state.flash_q
            st.rerun()

    if st.session_state.get('flipped'):
        st.markdown(f"""
            <div style="background-color: #E3F2FD; padding: 25px; border-radius: 15px; margin-top: 20px; border-left: 10px solid #1E88E5;">
                <p style="font-size: 1.8em; margin-bottom: 10px;"><b>拆解：</b> <span style="color: #D32F2F;">{q['breakdown']}</span></p>
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
    
    st.sidebar.title("🧬 Etymon Decoder")
    menu = st.sidebar.radio("導航", ["字根區", "學習區", "高中 7000 區", "醫學區", "法律區", "人工智慧區", "管理區"])
    
    st.sidebar.divider()
    if st.sidebar.button("強制刷新數據"): st.cache_data.clear(); st.rerun()

    if menu == "字根區":
        cats = ["全部顯示"] + sorted(list(set(c['category'] for c in data)))
        ui_search_page(data, st.sidebar.selectbox("分類篩選", cats))
    elif menu == "學習區":
        ui_quiz_page(data)
    elif menu == "高中 7000 區":
        hs = [c for c in data if any(k in c['category'] for k in ["高中", "7000"])]
        ui_domain_page(hs, "🎓 高中核心字根", "#2E7D32", "#E8F5E9")
    elif menu == "醫學區":
        med = [c for c in data if "醫學" in c['category']]
        ui_domain_page(med, "🩺 醫學專業術語", "#C62828", "#FFEBEE")
    elif menu == "法律區":
        law = [c for c in data if "法律" in c['category']]
        ui_domain_page(law, "⚖️ 法律術語區", "#4527A0", "#EDE7F6")
    elif menu == "人工智慧區":
        ai = [c for c in data if "人工智慧" in c['category'] or "AI" in c['category']]
        ui_domain_page(ai, "🤖 AI 與技術區", "#1565C0", "#E3F2FD")
    elif menu == "管理區":
        ui_admin_page(data)

if __name__ == "__main__":
    main()
