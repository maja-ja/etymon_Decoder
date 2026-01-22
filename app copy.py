import streamlit as st
import json
import os
import random
import pandas as pd

# ==========================================
# 1. 核心配置與雲端同步 (放在最前面)
# ==========================================
# 這是你的 Google 試算表 ID
SHEET_ID = '1W1ADPyf5gtGdpIEwkxBEsaJ0bksYldf4AugoXnq6Zvg'
GSHEET_URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv'
DB_FILE = 'etymon_database.json'
PENDING_FILE = 'pending_data.json'

def load_db():
    """加強版讀取：處理 Google Sheets 讀取時可能產生的引號問題"""
    try:
        # 讀取試算表
        df = pd.read_csv(GSHEET_URL)
        if df.columns.empty:
            return []
            
        # 取得 A1 的原始內容
        json_str = df.columns[0]
        
        # 關鍵修正：移除 Google Sheets CSV 可能自動包裹的外部引號
        json_str = json_str.strip()
        if json_str.startswith('"') and json_str.endswith('"'):
            json_str = json_str[1:-1].replace('""', '"')
            
        return json.loads(json_str)
    except Exception as e:
        # 可以在畫面上印出錯誤（除錯用，穩定後可刪除）
        # st.sidebar.error(f"雲端讀取失敗: {e}") 
        
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                try: return json.load(f)
                except: return []
    return []
def get_stats(data):
    if not data: return 0, 0
    total_cats = len(data)
    total_words = sum(len(g.get('vocabulary', [])) for cat in data for g in cat.get('root_groups', []))
    return total_cats, total_words

def merge_logic(pending_data):
    """合併邏輯：將新數據併入主資料庫並去重"""
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
                                added_words += 1
        # 同時儲存到本地
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(main_db, f, ensure_ascii=False, indent=2)
        return True, f"成功新增：{added_cats} 分類, {added_groups} 字根組, {added_words} 單字。"
    except Exception as e:
        return False, str(e)

# ==========================================
# 2. UI 頁面組件 (定義在邏輯之後)
# ==========================================

def ui_admin_page():
    st.title("🛠️ 數據管理後台")
    ADMIN_PASSWORD = "8787"
    
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False

    if not st.session_state.admin_authenticated:
        pwd_input = st.text_input("管理員密碼", type="password")
        if st.button("登入"):
            if pwd_input == ADMIN_PASSWORD:
                st.session_state.admin_authenticated = True
                st.rerun()
        return

    # 管理功能
    data = load_db()
    c_count, w_count = get_stats(data)
    
    st.subheader("🚀 雲端資料同步")
    st.write(f"目前單字總量：**{w_count}**")
    
    # 顯示 JSON 供複製到 Google Sheets
    json_text = json.dumps(data, ensure_ascii=False, indent=2)
    st.info("合併後，請點擊下方按鈕複製，並貼回 Google 試算表的 A1 儲存格，資料才不會在改程式時消失。")
    st.code(json_text, language="json")
    
    # 合併功能
    if st.button("🚀 從 Pending 檔案執行合併"):
        if os.path.exists(PENDING_FILE):
            with open(PENDING_FILE, 'r', encoding='utf-8') as f:
                new_data = json.load(f)
            success, msg = merge_logic(new_data)
            if success:
                st.success(msg)
                st.rerun()
def ui_medical_page(med_data):
    st.title("醫學術語專業區")
    st.info("醫學術語由字根、前綴與後綴組成。")

    all_med_roots = []
    for cat in med_data:
        for group in cat.get('root_groups', []):
            all_med_roots.append(f"{' / '.join(group['roots'])} → {group['meaning']}")
    
    selected_med = st.selectbox("快速定位醫學字根", all_med_roots)
    
    for cat in med_data:
        for group in cat.get('root_groups', []):
            label = f"{' / '.join(group['roots'])} → {group['meaning']}"
            with st.expander(f"核心字根：{label}", expanded=(label == selected_med)):
                cols = st.columns(2)
                for i, v in enumerate(group.get('vocabulary', [])):
                    with cols[i % 2]:
                        st.markdown(f"""
                        <div style="padding:20px; border-radius:12px; border-left:6px solid #ff4b4b; background-color:#ffffff; margin-bottom:15px; box-shadow:0 2px 8px rgba(0,0,0,0.05); color:#31333f !important;">
                            <h4 style="margin:0; color:#1f77b4;">{v['word']}</h4>
                            <p style="margin:10px 0; font-size:0.9rem; color:#666;">結構：<code>{v['breakdown']}</code></p>
                            <p style="margin:0; font-weight:bold; color:#31333f;">釋義：{v['definition']}</p>
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
    
    # 鎖定顏色避免手機吃字
    st.markdown(f"""
    <div style="background-color:#ffffff; padding:40px; border-radius:20px; border:1px solid #e0e0e0; text-align:center; min-height:280px; box-shadow:0 4px 15px rgba(0,0,0,0.05); color:#31333f !important;">
        <small style="color:#888;">{q['cat'].upper()}</small>
        <h1 style="font-size:3.5rem; margin:20px 0; color:#1f77b4;">{q['word']}</h1>
        {f'<hr style="border-top:1px solid #eee;"><p style="font-size:1.2rem; color:#0366d6;"><code>{q["breakdown"]}</code></p><h3 style="color:#31333f;">{q["definition"]}</h3>' if st.session_state.is_flipped else '<p style="color:#ccc; margin-top:50px;">點擊下方按鈕查看答案</p>'}
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    if not st.session_state.is_flipped:
        if st.button("查看答案", use_container_width=True):
            st.session_state.is_flipped = True
            st.rerun()
    else:
        c1, c2 = st.columns(2)
        if c1.button("⬅️ 翻回正面", use_container_width=True):
            st.session_state.is_flipped = False
            st.rerun()
        if c2.button("下一題 ➡️", use_container_width=True):
            if 'flash_q' in st.session_state: del st.session_state.flash_q
            st.session_state.is_flipped = False
            st.rerun()

# ==========================================
# 3. 主程序入口
# ==========================================
def main():
    st.write("雲端原始資料片段:", str(pd.read_csv(GSHEET_URL).columns[0])[:100])
    st.set_page_config(page_title="Etymon 智選", layout="wide")
    
    # 1. 讀取數據
    data = load_db()
    
    # 2. 側邊欄選單
    st.sidebar.title("Etymon Decoder")
    menu = st.sidebar.radio("功能導航", ["字根導覽", "記憶卡片", "醫學專區", "管理後台"])
    
    # 3. 顯示統計數據
    c, w = get_stats(data)
    st.sidebar.divider()
    st.sidebar.metric("總單字量", w)
    st.sidebar.caption("數據同步：Google Sheets")

    # 4. 根據選單切換頁面
    if menu == "管理後台":
        ui_admin_page()
        
    elif menu == "字根導覽":
        # 取得所有分類供篩選
        cats = ["全部顯示"] + sorted(list(set(c['category'] for c in data)))
        selected_cat = st.sidebar.selectbox("篩選分類", cats)
        ui_search_page(data, selected_cat)
        
    elif menu == "記憶卡片":
        ui_quiz_page(data)
        
    elif menu == "醫學專區":
        # 過濾出包含「醫學」關鍵字的分類數據
        med_data = [c for c in data if "醫學" in c['category']]
        if med_data:
            ui_medical_page(med_data)
        else:
            st.info("目前資料庫中尚無醫學分類數據。")

if __name__ == "__main__":
    main()
