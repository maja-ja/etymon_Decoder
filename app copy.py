import streamlit as st
import json
import random
import os
import re

# --- 基礎設定 ---
DB_FILE = 'etymon_database.json'

# --- 1. 密碼檢查功能 ---
'''def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if st.session_state["password_correct"]:
        return True
    st.title("🔐 歡迎來到詞根宇宙")
    password = st.text_input("訪問密碼：", type="password")
    if st.button("登入"):
        if password == "8888":
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("❌ 密碼錯誤")
    return False

if not check_password():
    st.stop()'''

# --- 2. 數據處理與解析引擎 ---
def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_data(new_data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, indent=4, ensure_ascii=False)

def parse_text_to_json(raw_text):
    """解析人類格式為 JSON"""
    new_data = []
    categories = re.split(r'「(.+?)」類', raw_text)
    for i in range(1, len(categories), 2):
        cat_name = categories[i]
        cat_body = categories[i+1]
        cat_obj = {"category": cat_name, "root_groups": []}
        root_blocks = re.split(r'\n(?=-)', cat_body)
        for block in root_blocks:
            root_info = re.search(r'-([\w/ \-]+)-\s*[\(（](.+?)[\)）]', block)
            if root_info:
                group = {
                    "roots": [r.strip() for r in root_info.group(1).split('/')],
                    "meaning": root_info.group(2).strip(),
                    "vocabulary": []
                }
                words = re.findall(r'(\w+)\s*[\(（](.+?)\s*=\s*(.+?)[\)）]', block)
                for w_name, w_logic, w_trans in words:
                    group["vocabulary"].append({"word": w_name.strip(), "breakdown": w_logic.strip(), "definition": w_trans.strip()})
                if group["vocabulary"]:
                    cat_obj["root_groups"].append(group)
        new_data.append(cat_obj)
    return new_data

data = load_data()

# --- 3. 側邊欄：大類選單與詞根導覽 ---
st.sidebar.title("🚀 詞根宇宙導航")
st.sidebar.markdown("---")

if not data:
    st.sidebar.warning("請先去數據工廠新增內容")
    mode = st.sidebar.radio("模式：", ["⚙️ 數據工廠"])
else:
    mode = st.sidebar.radio("切換模式：", ["🔍 導覽解碼", "✍️ 學習測驗", "⚙️ 數據工廠"])
    
    st.sidebar.markdown("---")
    all_categories = [item['category'] for item in data]
    selected_cat = st.sidebar.selectbox("選擇大類領域", all_categories)
    
    # 獲取當前大類的數據
    current_cat = next(item for item in data if item['category'] == selected_cat)
    st.sidebar.subheader(f"📍 {selected_cat} 包含：")
    for group in current_cat['root_groups']:
        st.sidebar.write(f"- {' / '.join(group['roots'])} ({group['meaning']})")

# --- 4. 模式執行邏輯 ---

if mode == "🔍 導覽解碼":
    st.title(f"🧩 {selected_cat} 解碼地圖")
    
    # 單字搜尋
    search_query = st.text_input("🔍 搜尋單字或詞根...", placeholder="輸入 dict, fac, predict...")
    
    if search_query:
        query = search_query.lower()
        for cat in data:
            for group in cat['root_groups']:
                match_words = [v for v in group['vocabulary'] if query in v['word'].lower()]
                if any(query in r.lower() for r in group['roots']) or match_words:
                    st.write(f"### 詞根: `{' / '.join(group['roots'])}` ({group['meaning']})")
                    for v in group['vocabulary']:
                        st.write(f"**{v['word']}** | `{v['breakdown']}` | {v['definition']}")
                    st.divider()
    else:
        # 顯示該大類下的所有內容 (導覽模式)
        for group in current_cat['root_groups']:
            with st.expander(f"📦 詞根族：{' / '.join(group['roots'])} ({group['meaning']})", expanded=True):
                cols = st.columns(2)
                for idx, v in enumerate(group['vocabulary']):
                    with cols[idx % 2]:
                        st.markdown(f"**{v['word']}**")
                        st.caption(f"拆解：{v['breakdown']}  \n含義：{v['definition']}")

elif mode == "✍️ 學習測驗":
    st.title("✍️ 詞根解碼測驗")
    st.info("模式已就緒，請開始挑戰。")
    all_words = []
    for cat in data:
        for group in cat['root_groups']:
            for v in group['vocabulary']:
                all_words.append({**v, "root_meaning": group['meaning']}) #

    if 'q' not in st.session_state:
        st.session_state.q = random.choice(all_words)
        st.session_state.show = False
    q = st.session_state.q
    st.subheader(f"單字：:blue[{q['word']}]")
    
    ans_type = st.radio("你想猜什麼？", ["中文含義", "拆解邏輯"])
    user_ans = st.text_input("輸入答案：")
    
    if st.button("查看答案"):
        st.session_state.show = True
    
    if st.session_state.show:
        truth = q['definition'] if ans_type == "中文含義" else q['breakdown']
        st.info(f"正確答案：{truth}")
        if st.button("下一題"):
            st.session_state.q = random.choice(all_words)
            st.session_state.show = False
            st.rerun()
