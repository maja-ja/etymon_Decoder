import streamlit as st
import json
import random
import os

# --- 基礎配置 ---
DB_FILE = 'etymon_database2.json'
st.set_page_config(page_title="詞根宇宙：學習與管理", layout="wide")

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_data(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

data = load_data()

# --- 側邊欄導航 ---
st.sidebar.title("🚀 詞根宇宙入口")
mode = st.sidebar.radio("切換模式：", ["🔍 搜尋解碼", "✍️ 學習測驗", "⚙️ 數據擴充"])

# --- 模式一：搜尋解碼 ---
if mode == "🔍 搜尋解碼":
    st.title("🧩 Etymon Decoder")
    search_query = st.text_input("輸入單字或詞根...", placeholder="例如: Predict, Bio...")
    
    if search_query:
        query = search_query.lower()
        for cat in data:
            for group in cat['root_groups']:
                # 檢查詞根或單字是否匹配
                match_words = [v for v in group['vocabulary'] if query in v['word'].lower()]
                if any(query in r.lower() for r in group['roots']) or match_words:
                    st.write(f"### 詞根：`{' / '.join(group['roots'])}` ({group['meaning']})")
                    for v in group['vocabulary']:
                        st.write(f"**{v['word']}** | `{v['breakdown']}` | {v['definition']}")
                    st.divider()

# --- 模式二：學習測驗 ---
elif mode == "✍️ 學習測驗":
    st.title("✍️ 詞根挑戰")
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
    st.write(f"提示：詞根含義與「{q['root_meaning']}」有關")
    
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

# --- 模式三：數據擴充 ---
elif mode == "⚙️ 數據擴充":
    st.title("⚙️ 數據同步")
    st.write("將 Gemini 產出的 JSON 貼在下面即可完成擴充。")
    current_json = json.dumps(data, indent=4, ensure_ascii=False)
    new_json = st.text_area("JSON 編輯區", value=current_json, height=400)
    if st.button("儲存資料庫"):
        try:
            save_data(json.loads(new_json))
            st.success("更新成功！")
        except:
            st.error("JSON 格式錯誤")