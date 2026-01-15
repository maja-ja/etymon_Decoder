import streamlit as st
import json
import random
DB_FILE = 'etymon_database.json'
# --- 頁面設定 ---
st.set_page_config(page_title="詞根宇宙：解碼 AI 導航", layout="wide")
def save_data(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
# --- 讀取數據 ---
@st.cache_data
def load_data():
    with open('etymon_database.json', 'r', encoding='utf-8') as f:
        return json.load(f)

data = load_data()

# --- 側邊欄：導航與分類 ---
st.sidebar.title("🚀 詞根宇宙導航")
st.sidebar.markdown("---")

all_categories = [item['category'] for item in data]
selected_cat = st.sidebar.selectbox("選擇知識領域", all_categories)

# 顯示該大類下的所有詞根
current_cat_data = next(item for item in data if item['category'] == selected_cat)
st.sidebar.subheader(f"📍 {selected_cat}")
for group in current_cat_data['root_groups']:
    roots_display = " / ".join(group['roots'])
    st.sidebar.write(f"- {roots_display} ({group['meaning']})")

st.sidebar.markdown("---")
st.sidebar.info("這是利用 AI 協作開發的語義解碼系統，專注於邏輯學習而非死背。")

# --- 主介面 ---
st.title("🧩 Etymon Decoder 語源解碼器")
st.markdown(f"### 當前探索區域：`{selected_cat}`")

# 搜尋功能
search_query = st.text_input("🔍 輸入單字或詞根來解碼...", placeholder="例如: Predict, Bio, Port...")

# 搜尋邏輯
if search_query:
    found = False
    query = search_query.lower()
    
    for cat in data:
        for group in cat['root_groups']:
            # 檢查詞根
            root_match = any(query in r.lower() for r in group['roots'])
            # 檢查單字
            words_match = [v for v in group['vocabulary'] if query in v['word'].lower()]
            
            if root_match or words_match:
                found = True
                with st.container():
                    st.divider()
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        st.markdown(f"### 詞根: `{' / '.join(group['roots'])}`")
                        st.write(f"**核心含義:** {group['meaning']}")
                    with col2:
                        for v in group['vocabulary']:
                            # 如果搜尋單字，特別標註該單字
                            is_target = query in v['word'].lower()
                            display_text = f"**{v['word']}** \n解構: `{v['breakdown']}`  \n含義: {v['definition']}"
                            if is_target:
                                st.success(display_text)
                            else:
                                st.write(display_text)
    if not found:
        st.warning("找不到相關結果，請嘗試其他關鍵字。")

else:
    # 預設首頁展示：隨機推薦
    st.write("請從左側選擇分類，或在上方搜尋。")
    st.info("💡 隨機推薦一個詞根家族：")
    
    random_group = random.choice(current_cat_data['root_groups'])
    st.subheader(f"本站推薦：`-{' / '.join(random_group['roots'])}-` ({random_group['meaning']})")
    
    cols = st.columns(len(random_group['vocabulary'][:3]))
    for i, v in enumerate(random_group['vocabulary'][:3]):
        with cols[i]:
            st.metric(label=v['word'], value=v['definition'])
            st.caption(f"拆解: {v['breakdown']}")
# --- 介面 ---
st.set_page_config(page_title="詞根宇宙管理員", layout="wide")
tab1, tab2 = st.tabs(["🔍 詞根搜尋", "⚙️ 數據管理"])

data = load_data()

with tab1:
    st.title("🧩 Etymon Decoder")
    # ... (保留你之前的搜尋邏輯程式碼) ...
    st.info("請到 '數據管理' 分頁更新你的單字庫")

with tab2:
    st.title("🛠 數據庫手動更新")
    st.markdown("將 Gemini 產出的 JSON 代碼貼在下方：")
    
    # 顯示目前的 JSON 方便修改
    current_json_str = json.dumps(data, indent=4, ensure_ascii=False)
    new_json_str = st.text_area("JSON 數據區", value=current_json_str, height=400)
    
    if st.button("💾 儲存並更新資料庫"):
        try:
            new_data = json.loads(new_json_str)
            save_data(new_data)
            st.success("資料庫已成功更新！請重新整理頁面。")
        except Exception as e:
            st.error(f"JSON 格式有誤，請檢查：{e}")
# --- 商業底部 (Call to Action) ---
st.markdown("---")
col_a, col_b, col_c = st.columns(3)
with col_a:
    st.button("🔓 訂閱 API 數據授權")
with col_b:
    st.button("📘 獲取完整 Notion 模板")
with col_c:
    st.button("💬 聯絡專家開發")