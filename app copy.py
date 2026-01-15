import streamlit as st
import json
import os
from datetime import datetime
import re
import random
import requests
import base64

# --- 基礎設定與版本 ---
VERSION = "pre1.0"
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
is_wish_anon = st.sidebar.checkbox("匿名許願")
if st.sidebar.button("提交願望"):
    if wish_word:
        user = "Anonymous" if is_wish_anon else "User"
        wish_entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {user}: {wish_word}\n"
        if save_to_github(wish_entry, WISH_FILE, is_json=False):
            st.sidebar.success("願望已永久同步至 GitHub！")
        else:
            st.sidebar.error("同步失敗，請檢查 Token 設定。")

# --- 主介面邏輯 ---

if mode == "🔍 導覽解碼":
    def show_search():
        query = st.text_input("🔍 搜尋...", placeholder="dict, cap, factor...")
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
            if not found: st.warning("還沒做出來抱歉><")
    render_section("導覽解碼系統", show_search)

elif mode == "⚙️ 數據管理":
    def show_factory():
        st.info("📦 此處提交的數據將直接更新在GitHub，然後作者會在小改版上傳。")
        with st.expander("📌 查看標準輸入格式提示", expanded=False):
            st.code("「類別」類\n-字根-(解釋)\n單詞((根)(義)+(根)(義)=含義)", language="text")

        raw_input = st.text_area("數據貼上區", height=300)
        c_name = st.text_input("貢獻者名稱")
        c_deed = st.text_input("本次事蹟")
        is_c_anon = st.checkbox("匿名貢獻")

        if st.button("🚀 提交至 GitHub 隔離區"):
            if raw_input:
                parsed = parse_text_to_json(raw_input)
                if parsed:
                    # 1. 同步數據至 GitHub
                    if save_to_github(parsed, PENDING_FILE, is_json=True):
                        # 2. 同步貢獻者名單至 GitHub
                        contrib_entry = [{
                            "name": "Anonymous" if is_c_anon else (c_name if c_name else "Anonymous"),
                            "deed": c_deed,
                            "date": datetime.now().strftime('%Y-%m-%d')
                        }]
                        save_to_github(contrib_entry, CONTRIB_FILE, is_json=True)
                        
                        st.success("✅ 數據已成功寫回 GitHub 檔案！")
                        st.balloons()
                    else:
                        st.error("❌ GitHub 寫入失敗，請確認 Secrets。")
                else:
                    st.error("❌ 解析失敗，請檢查格式。")
    render_section("數據工廠與隔離區", show_factory)

elif mode == "✍️ 學習測驗":
    all_words = []
    for cat in data:
        for group in cat['root_groups']:
            for v in group['vocabulary']:
                all_words.append({**v, "root_meaning": group['meaning']})

    if not all_words:
        st.warning("資料庫暫無內容。")
    else:
        if 'q' not in st.session_state:
            st.session_state.q = random.choice(all_words)
            st.session_state.show = False
        
        q = st.session_state.q
        st.subheader(f"挑戰單字：:blue[{q['word']}]")
        st.caption(f"提示：詞根含義為 「{q['root_meaning']}」")
        
        ans_type = st.radio("測驗類型", ["中文含義", "拆解邏輯"])
        if st.button("查看答案"): st.session_state.show = True
        
        if st.session_state.show:
            st.success(f"答案：{q['definition'] if ans_type == '中文含義' else q['breakdown']}")
            if st.button("下一題"):
                st.session_state.q = random.choice(all_words)
                st.session_state.show = False
                st.rerun()

elif mode == "🤝 合作招募":
    render_section("合作招募中心", lambda: st.info("我們需要 1. SQLite 小幫手 2. 整理資料的小幫手 3. CSV 小幫手 （薪資暫無因爲開發者高二而已）聯繫方式：私訊 Instagram/Threads 或寄信至 kadowsella@gmail.com"))

st.markdown(f"<center style='color:gray; font-size:0.8em;'>詞根宇宙 {VERSION}</center>", unsafe_allow_html=True)
