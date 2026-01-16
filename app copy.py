import streamlit as st
import json
import os
from datetime import datetime
import re
import random
import requests
import base64

# --- 基礎設定與版本 ---
VERSION = "V1.1"
DB_FILE = 'etymon_database.json'
CONTRIB_FILE = 'contributors.json'
WISH_FILE = 'wish_list.txt'
PENDING_FILE = 'pending_data.json'

# --- GitHub API 數據同步函式 ---
def save_to_github(new_data, filename, is_json=True):
    """
    將資料安全同步回 GitHub 倉庫。
    secrets 中需設定：GITHUB_TOKEN, GITHUB_REPO (格式: 帳號/專案名)
    """
    try:
        token = st.secrets["GITHUB_TOKEN"]
        repo = st.secrets["GITHUB_REPO"]
        url = f"https://api.github.com/repos/{repo}/contents/{filename}"
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

        # 1. 抓取舊檔案 SHA
        r = requests.get(url, headers=headers)
        sha = r.json().get("sha") if r.status_code == 200 else None
        
        # 2. 合併資料邏輯
        if is_json:
            current_content = []
            if r.status_code == 200:
                content_decoded = base64.b64decode(r.json()["content"]).decode("utf-8")
                try:
                    current_content = json.loads(content_decoded)
                except:
                    current_content = []
            current_content.extend(new_data)
            final_string = json.dumps(current_content, indent=4, ensure_ascii=False)
        else:
            # 純文字檔案 (許願池)
            current_string = ""
            if r.status_code == 200:
                current_string = base64.b64decode(r.json()["content"]).decode("utf-8")
            final_string = current_string + new_data

        # 3. 推送回去
        payload = {
            "message": f"🤖 自動更新: {filename} via App",
            "content": base64.b64encode(final_string.encode("utf-8")).decode("utf-8"),
            "sha": sha
        }
        res = requests.put(url, json=payload, headers=headers)
        return res.status_code in [200, 201]
    except Exception as e:
        st.error(f"GitHub 同步出錯：{e}")
        return False

# --- 數據讀取函式 ---
def load_json(file_path, default_val):
    # 本地端讀取（用於顯示搜尋結果）
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            try: return json.load(f)
            except: return default_val
    return default_val

# --- 數據解析引擎 ---
def parse_text_to_json(raw_text):
    new_data = []
    cleaned = raw_text.replace('（', '(').replace('）', ')').replace('－', '-').replace('「', '"').replace('」', '"')
    categories = re.split(r'["\'](.+?)["\']類', cleaned)
    for i in range(1, len(categories), 2):
        cat_name = categories[i].strip()
        cat_body = categories[i+1]
        cat_obj = {"category": cat_name, "root_groups": []}
        root_blocks = re.split(r'\n(?=-)', cat_body)
        for block in root_blocks:
            root_info = re.search(r'-([\w/ \-]+)-\s*\((.+?)\)', block)
            if root_info:
                group = {
                    "roots": [r.strip() for r in root_info.group(1).split('/')],
                    "meaning": root_info.group(2).strip(),
                    "vocabulary": []
                }
                word_matches = re.findall(r'(\w+)\s*\((.+?)\)', block)
                for w_name, w_logic in word_matches:
                    logic_part, def_part = w_logic.split('=', 1) if "=" in w_logic else (w_logic, "待審核")
                    group["vocabulary"].append({
                        "word": w_name.strip(),
                        "breakdown": logic_part.strip(),
                        "definition": def_part.strip()
                    })
                if group["vocabulary"]:
                    cat_obj["root_groups"].append(group)
        if cat_obj["root_groups"]:
            new_data.append(cat_obj)
    return new_data

# 預載數據
data = load_json(DB_FILE, [])

# --- 模組化區塊 ---
def render_section(title, content_func):
    with st.container():
        st.markdown(f"### {title}")
        content_func()
        st.divider()

# --- 頁面配置 ---
st.set_page_config(page_title="詞根宇宙：解碼導航", layout="wide")

# --- 側邊欄 ---
st.sidebar.title("🚀 詞根宇宙")
st.sidebar.caption(f"當前版本：{VERSION}")
mode = st.sidebar.radio("導航選單", ["🔍 導覽解碼", "✍️ 學習測驗", "⚙️ 數據管理", "🤝 合作招募"])

# 側邊欄：許願池 (同步至 GitHub)
st.sidebar.markdown("---")
st.sidebar.subheader("🎯 零散單字許願")
wish_word = st.sidebar.text_input("想要新增的單字", placeholder="例如: Metaphor")
if st.sidebar.button("提交願望"):
    if wish_word:
        user = "Anonymous"
        wish_entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {user}: {wish_word}\n"
        if save_to_github(wish_entry, WISH_FILE, is_json=False):
            st.sidebar.success("願望已永久同步至 GitHub！")
        else:
            st.sidebar.error("同步失敗，請檢查 Token 設定。")
# --- 主介面邏輯 ---
if mode == "🔍 導覽解碼":
    def show_search():
        # --- 隨機預覽邏輯 ---
        if 'preview_words' not in st.session_state:
            all_v = []
            for cat in data:
                for group in cat['root_groups']:
                    for v in group['vocabulary']:
                        all_v.append({**v, "cat": cat['category'], "roots": group['roots'], "meaning": group['meaning']})
            # 隨機挑選 3 個
            st.session_state.preview_words = random.sample(all_v, min(len(all_v), 3)) if all_v else []

        # 顯示隨機預覽卡片
        if st.session_state.preview_words:
            cols = st.columns(3)
            for i, word_info in enumerate(st.session_state.preview_words):
                with cols[i]:
                    st.markdown(
                        f"""
                        <div style="border:1px solid #e6e9ef; border-radius:10px; padding:15px; background-color:#f8f9fa; height:150px">
                            <h5 style="margin:0; color:#007bff;">{word_info['word']}</h5>
                            <p style="font-size:0.6em; color:gray; margin:5px 0;">{word_info['cat']} | {'/'.join(word_info['roots'])}</p>
                            <p style="font-size:0.7em; margin:0;">{word_info['definition'][:20]}...</p>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
            
            if st.button("🔄 換一批試試", key="refresh_preview"):
                del st.session_state.preview_words
                st.rerun()
        
        st.divider()

        # --- 原有的搜尋邏輯 ---
        query = st.text_input("🔍 搜尋...", placeholder="輸入字根或單字，例如: dict, cap, factor...", key="main_search_input")
        if query:
            q = query.lower().strip()
            found = False
            for cat in data:
                for group in cat['root_groups']:
                    root_match = any(q in r.lower() for r in group['roots'])
                    matched_v = [v for v in group['vocabulary'] if q in v['word'].lower()]
                    if root_match or matched_v:
                        found = True
                        st.markdown(f"#### 🧬 {cat['category']} | `{' / '.join(group['roots'])}` ({group['meaning']})")
                        for v in group['vocabulary']:
                            is_target = q in v['word'].lower()
                            with st.expander(f"{'⭐ ' if is_target else ''}{v['word']}", expanded=is_target):
                                st.write(f"**拆解：** `{v['breakdown']}`")
                                st.write(f"**含義：** {v['definition']}")
            if not found: st.warning("目前資料庫中尚無此內容，我們會儘快新增！")
            
    render_section("導覽解碼系統", show_search)
elif mode == "⚙️ 數據管理":
    def show_factory():
        st.info("📦 此處提交的數據將直接更新在 GitHub 隔離區，由作者審核後於小改版正式發布。")
        
        # 1. 格式範本與提示詞區域
        with st.expander("💡 快速上手：如何使用 AI 協助貢獻？", expanded=True):
            st.markdown("##### 第一步：複製下方提示詞")
            # 這裡定義推薦的提示詞
            prompt_text = """例：請幫我列出 5 個符合台灣「學測 5、6 級」程度的英文單字，並嚴格按照以下格式輸出：

「（分類名稱）」類
-字根-（字根含義)
單字（（字根1）（含義）+（字根2）（含義）=總義）

範例：
「心靈感知」類
-path-（感覺/感情)
sympathy（（sym）（共同）+（pathy）（感情）=同情心）"""
            
            st.code(prompt_text, language="text")
            
            st.markdown("##### 第二步：將 AI 生成的結果（範例）貼入下方區域")
            st.caption("⚠️ 系統會自動將全形括號轉換，請安心輸入。")

        # 2. 數據輸入區
        raw_input = st.text_area("🚀 數據貼上區", height=300, placeholder="在此貼上 AI 生成的內容...", key="factory_data_area")
        
        col1, col2 = st.columns(2)
        with col1:
            c_name = st.text_input("貢獻者暱稱", placeholder="用於內部記錄", key="factory_user_name")
        with col2:
            is_anon = st.checkbox("我希望匿名貢獻", key="factory_anon_check")

        if st.button("🚀 提交至 GitHub 隔離區", key="factory_submit_btn"):
            if not raw_input.strip():
                st.warning("請輸入內容後再提交。")
            else:
                parsed = parse_text_to_json(raw_input)
                if parsed:
                    if save_to_github(parsed, PENDING_FILE, is_json=True):
                        contrib_entry = [{
                            "name": "Anonymous" if is_anon else (c_name if c_name else "Anonymous"),
                            "date": datetime.now().strftime('%Y-%m-%d'),
                            "type": "Data Contribution"
                        }]
                        save_to_github(contrib_entry, CONTRIB_FILE, is_json=True)
                        st.success("✅ 數據已成功送達 GitHub！")
                        st.balloons()
                    else:
                        st.error("❌ GitHub 同步失敗，請檢查 Secrets 設定。")
                else:
                    st.error("❌ 解析失敗！請檢查類別標籤「」或字根標記 - - 是否正確。")
                    
    render_section("數據工廠：詞根解碼投稿", show_factory)
elif mode == "✍️ 學習測驗":
    all_words = []
    for cat in data:
        for group in cat['root_groups']:
            for v in group['vocabulary']:
                all_words.append({**v, "root_meaning": group['meaning']})

    if not all_words:
        st.warning("資料庫暫無內容，請先至數據管理提交數據。")
    else:
        if 'q' not in st.session_state:
            st.session_state.q = random.choice(all_words)
            st.session_state.show = False
        
        q = st.session_state.q
        st.subheader(f"挑戰單字：:blue[{q['word']}]")
        
        user_ans = st.text_input("在此寫下你的答案（自由輸入練習）：", key="quiz_answer_input")
        
        ans_type = st.radio("測驗類型", ["中文含義", "拆解邏輯"], key="quiz_type_radio")
        if st.button("查看正確答案", key="quiz_show_btn"): 
            st.session_state.show = True
        
        if st.session_state.show:
            st.success(f"參考答案：{q['definition'] if ans_type == '中文含義' else q['breakdown']}")
            if st.button("下一題", key="quiz_next_btn"):
                st.session_state.q = random.choice(all_words)
                st.session_state.show = False
                st.rerun()

elif mode == "🤝 合作招募":
    def show_recruit():
        st.info("我們正在尋找以下夥伴：")
        st.markdown("""
        1. **📊 SQLite 小幫手**：協助數據庫架構優化。
        2. **🧹 數據整理員**：校對詞根含義。
        3. **✍️ 社群文案策劃**：推廣詞根宇宙。
        
        **(適合特殊選材（應該）、學習歷程需求！)**
        """)
        st.write("📩 聯繫方式：私訊 Instagram/Threads 或寄信至 `kadowsella@gmail.com`")
    render_section("合作招募中心", show_recruit)

# 版本號顯示
st.markdown(f"<center style='color:gray; font-size:0.8em;'>詞根宇宙 {VERSION}</center>", unsafe_allow_html=True)
