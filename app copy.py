import datetime
import streamlit as st
import json
import os
import time
import random
import pandas as pd
import base64
import re
from io import BytesIO
from gtts import gTTS
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. 配置與全域設定 (Config & CSS)
# ==========================================
st.set_page_config(page_title="Etymon Decoder", page_icon="🧩", layout="wide")

SHEET_ID = '1W1ADPyf5gtGdpIEwkxBEsaJ0bksYldf4AugoXnq6Zvg'
GSHEET_URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv'
FEEDBACK_URL = st.secrets.get("feedback_sheet_url") # 需確認 secrets 是否設定

def inject_custom_css():
    """注入全域自適應 CSS"""
    st.markdown("""
        <style>
            /* 1. 基礎字體比例加大 */
            html { font-size: 20px; } 

            /* 2. 手機端 (大字體優化) */
            @media (max-width: 600px) {
                .responsive-word { font-size: 15vw !important; margin-bottom: 10px; }
                .responsive-breakdown { font-size: 6vw !important; padding: 10px 15px !important; }
                .responsive-text { font-size: 5.5vw !important; line-height: 1.5; }
                .stButton button { height: 3.5rem; font-size: 1.2rem !important; }
            }

            /* 3. 電腦端 (清晰大字) */
            @media (min-width: 601px) {
                .responsive-word { font-size: 4rem !important; }
                .responsive-breakdown { font-size: 2rem !important; }
                .responsive-text { font-size: 1.5rem !important; }
            }

            /* 4. 構造拆解框 */
            .breakdown-container {
                font-family: 'Courier New', monospace;
                font-weight: bold;
                background-color: var(--secondary-background-color); 
                color: var(--text-color); 
                padding: 12px 20px;
                border-radius: 12px;
                border: 2px solid var(--primary-color);
                display: inline-block;
                margin: 10px 0;
            }

            /* 5. 側邊欄與其他元件優化 */
            .stats-container {
                text-align: center; 
                padding: 20px; 
                background-color: var(--secondary-background-color); 
                border-radius: 15px; 
                color: var(--text-color);
            }
            .stSelectbox div[role="button"] input { caret-color: transparent !important; pointer-events: none !important; }
            div[data-testid="stPills"] button { font-size: 1.1rem !important; padding: 8px 16px !important; }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 核心工具函式 (Utils: Audio, DB, Feedback)
# ==========================================
def speak(text):
    """使用 JavaScript 強制觸發瀏覽器音訊播放 (HTML5 Audio)"""
    try:
        tts = gTTS(text=text, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        audio_base64 = base64.b64encode(fp.read()).decode()
        unique_id = f"audio_{int(time.time() * 1000)}"
        
        audio_html = f"""
            <div id="{unique_id}"></div>
            <script>
                (function() {{
                    var audio = new Audio("data:audio/mp3;base64,{audio_base64}");
                    audio.play().catch(function(error) {{
                        console.log("播放被瀏覽器阻擋，嘗試手動觸發", error);
                    }});
                }})();
            </script>
        """
        st.components.v1.html(audio_html, height=0)
    except Exception as e:
        st.error(f"語音錯誤: {e}")

@st.cache_data(ttl=600)
def load_db():
    """讀取並結構化 Google Sheet 資料"""
    BLOCKS = ["A:I", "J:R", "S:AA", "AB:AJ", "AK:AS"]
    COL_NAMES = ['category', 'roots', 'meaning', 'word', 'breakdown', 'definition', 'phonetic', 'example', 'translation']
    
    all_dfs = []
    for rng in BLOCKS:
        try:
            url = f"{GSHEET_URL}&range={rng}"
            df_part = pd.read_csv(url, skiprows=1, names=COL_NAMES)
            df_part = df_part.dropna(subset=['category', 'word'], how='all')
            if not df_part.empty:
                all_dfs.append(df_part)
        except Exception:
            continue

    if not all_dfs: return []
    df = pd.concat(all_dfs, ignore_index=True)
    df = df[df['category'] != 'category'] # 移除重複標題
    
    structured_data = []
    for cat_name, cat_group in df.groupby('category'):
        root_groups = []
        for (roots, meaning), group_df in cat_group.groupby(['roots', 'meaning']):
            vocabulary = []
            for _, row in group_df.iterrows():
                vocabulary.append({
                    "word": str(row['word']),
                    "breakdown": str(row['breakdown']),
                    "definition": str(row['definition']),
                    "phonetic": str(row['phonetic']) if pd.notna(row['phonetic']) else "",
                    "example": str(row['example']) if pd.notna(row['example']) else "",
                    "translation": str(row['translation']) if pd.notna(row['translation']) else ""
                })
            root_groups.append({
                "roots": [r.strip() for r in str(roots).split('/')],
                "meaning": str(meaning),
                "vocabulary": vocabulary
            })
        structured_data.append({"category": str(cat_name), "root_groups": root_groups})
    return structured_data

def get_stats(data):
    if not data: return 0, 0
    total_words = sum(len(g.get('vocabulary', [])) for cat in data for g in cat.get('root_groups', []))
    return len(data), total_words

def save_feedback_to_gsheet(word, feedback_type, comment):
    """儲存回報至 Google Sheet"""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=FEEDBACK_URL, ttl=0)
        new_row = pd.DataFrame([{
            "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "word": word, "type": feedback_type, "comment": comment, "status": "pending"
        }])
        updated_df = pd.concat([df, new_row], ignore_index=True)
        conn.update(spreadsheet=FEEDBACK_URL, data=updated_df)
        st.success(f"單字「{word}」的回報已同步至雲端！")
    except Exception as e:
        st.error(f"雲端同步失敗: {e}")

# ==========================================
# 3. UI 元件 (Components)
# ==========================================
def ui_time_based_lofi():
    """側邊欄時鐘與 Lofi 音樂"""
    utc_now = datetime.datetime.utcnow()
    tw_now = utc_now + datetime.timedelta(hours=8)
    hour = tw_now.hour

    if 6 <= hour < 12:
        mode, vid, icon = "晨間能量 (Morning)", "jfKfPfyJRdk", "🌅"
    elif 12 <= hour < 18:
        mode, vid, icon = "午後專注 (Study)", "jfKfPfyJRdk", "📖"
    elif 18 <= hour < 23:
        mode, vid, icon = "晚間複習 (Chill)", "28KRPhVzCus", "🛋️"
    else:
        mode, vid, icon = "深夜療癒 (Sleep)", "28KRPhVzCus", "😴"

    with st.sidebar.expander(f"🎵 時光音樂：{mode}", expanded=True):
        st.write(f"🕒 台灣時間：{tw_now.strftime('%H:%M')}")
        embed_code = f"""
            <div style="border-radius:12px; overflow:hidden; border: 1px solid #ddd; background: #000;">
                <iframe width="100%" height="200" 
                    src="https://www.youtube.com/embed/{vid}?rel=0&modestbranding=1&playsinline=1&autoplay=0" 
                    frameborder="0" allowfullscreen>
                </iframe>
            </div>
        """
        st.markdown(embed_code, unsafe_allow_html=True)
        st.caption(f"目前處於 {icon} 時段。")

def ui_newbie_whiteboard():
    """新手教學白板"""
    st.markdown("""
    <div style="background-color: var(--secondary-background-color); padding: 25px; border-radius: 15px; border: 2px dashed var(--primary-color);">
        <h2 style="margin-top:0; text-align:center;">歡迎使用 Etymon Decoder</h2>
        <p style="text-align:center; opacity:0.8;">拆解積木，從根本理解英文。</p>
        <hr>
        <h4 style="color:var(--primary-color);">使用步驟：</h4>
        <ul class="responsive-text">
            <li><b>第一步：</b> 從左側選單選擇適合你的領域（如：國中區）。</li>
            <li><b>第二步：</b> 在搜尋框輸入字根 (如 <code>bio</code>) 或含義。</li>
            <li><b>第三步：</b> 點擊播放聆聽發音，觀察單字拆解。</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

def ui_feedback_component(word):
    """單字錯誤回報按鈕"""
    with st.popover("錯誤回報"):
        st.write(f"回報單字：**{word}**")
        f_type = st.selectbox("錯誤類型", ["發音錯誤", "拆解有誤", "中文釋義錯誤", "分類錯誤", "其他"], key=f"err_type_{word}")
        f_comment = st.text_area("詳細說明", placeholder="請描述正確的資訊...", key=f"err_note_{word}")
        if st.button("提交回報", key=f"err_btn_{word}"):
            if f_comment.strip() == "": st.error("請填寫說明內容")
            else: save_feedback_to_gsheet(word, f_type, f_comment)

# ==========================================
# 4. 主要頁面邏輯 (Page Functions)
# ==========================================

# --- A. 學習與字根區 (Learning Page) ---
def ui_domain_page(domain_data, title, theme_color, bg_color):
    """領域學習主頁面：透過字根篩選單字"""
    st.markdown(f'<h1 class="responsive-title">{title}</h1>', unsafe_allow_html=True)
    
    # 建立字根映射表
    root_map = {}
    for cat in domain_data:
        for group in cat.get('root_groups', []):
            label = f"{'/'.join(group['roots'])} ({group['meaning']})"
            root_map[label] = group
    
    search_query = st.text_input("輸入字根或含義進行篩選", placeholder="例如：act, bio, 動作, 生命...")
    
    filtered_labels = [label for label in root_map.keys() if search_query.lower() in label.lower()]

    if search_query:
        if filtered_labels:
            for label in filtered_labels:
                group = root_map[label]
                with st.expander(f"字根：{label}", expanded=True):
                    for v in group.get('vocabulary', []):
                        st.markdown(f'<div class="responsive-word" style="font-weight:bold; color:{theme_color};">{v["word"]}</div>', unsafe_allow_html=True)
                        col_play, col_report, _ = st.columns([1, 1, 2])
                        with col_play:
                            if st.button("播放", key=f"s_{v['word']}_{label}"): speak(v['word'])
                        with col_report:
                            ui_feedback_component(v['word'])
                        
                        st.markdown(f"""
                            <div style="margin-top: 10px;">
                                <span class="responsive-text" style="opacity: 0.8;">構造拆解：</span><br>
                                <div class="breakdown-container responsive-breakdown">{v['breakdown']}</div>
                                <div class="responsive-text" style="margin-top: 10px;">
                                    <b>中文定義：</b> {v['definition']}
                                </div>
                            </div>
                            <hr style="margin: 20px 0; opacity: 0.1;">
                        """, unsafe_allow_html=True)
        else:
            st.info("找不到相關字根，請查明關鍵字。")
    else:
        st.info("請在上方輸入框輸入字根開始探索。")

# --- B. 測驗中心 (Quiz Page) ---
def ui_quiz_page(data, selected_cat_from_sidebar):
    # 狀態管理
    if "active_cat" not in st.session_state: st.session_state.active_cat = selected_cat_from_sidebar
    if st.session_state.active_cat != selected_cat_from_sidebar:
        # 切換領域時重置測驗狀態
        for key in ['cloze_q', 'mc_q', 'flash_idx', 'flipped', 'mc_q_data']:
            if key in st.session_state: st.session_state[key] = None
        st.session_state.active_cat = selected_cat_from_sidebar
        st.rerun()

    modes = ["隨機字卡", "四選一測驗", "克漏字挑戰"]
    if "quiz_mode_idx" not in st.session_state: st.session_state.quiz_mode_idx = 0

    st.markdown('<h2 class="responsive-title">測驗中心</h2>', unsafe_allow_html=True)
    selected_mode = st.radio("選擇挑戰模式", modes, index=st.session_state.quiz_mode_idx, horizontal=True)
    st.session_state.quiz_mode_idx = modes.index(selected_mode)

    # 建立題庫
    if selected_cat_from_sidebar == "全部顯示":
        pool = [{**v, "cat": c['category']} for c in data for g in c['root_groups'] for v in g['vocabulary']]
    else:
        pool = [{**v, "cat": c['category']} for c in data if c['category'] == selected_cat_from_sidebar for g in c['root_groups'] for v in g['vocabulary']]
    
    if not pool:
        st.error("此範圍無資料，請先選擇有效分類。")
        return

    # 路由到具體題型
    if selected_mode == "隨機字卡": render_flashcard_mode(pool)
    elif selected_mode == "四選一測驗": render_multiple_choice_mode(pool)
    elif selected_mode == "克漏字挑戰": render_cloze_test_mode(pool)

def render_flashcard_mode(pool):
    if 'flash_idx' not in st.session_state or st.session_state.flash_idx is None:
        st.session_state.flash_idx = random.randint(0, len(pool)-1)
        st.session_state.flipped = False
    
    q = pool[st.session_state.flash_idx]
    st.markdown(f"""
        <div style="border: 2px solid var(--primary-color); border-radius: 15px; padding: 40px; text-align: center; background: var(--secondary-background-color);">
            <div style="font-size: 2.5rem; font-weight: bold; color: var(--primary-color);">{q['word']}</div>
        </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    if c1.button("答案 / 播放", use_container_width=True):
        st.session_state.flipped = True
        speak(q['word'])
    if c2.button("➡️ 下一張", use_container_width=True):
        st.session_state.flash_idx = random.randint(0, len(pool)-1)
        st.session_state.flipped = False
        st.rerun()

    if st.session_state.get('flipped'):
        st.info(f" **定義：** {q['definition']} \n\n 🏗️ **拆解：** `{q['breakdown']}`")

def render_multiple_choice_mode(pool):
    if 'mc_q_data' not in st.session_state or st.session_state.mc_q_data is None:
        target = random.choice(pool)
        all_defs = [x['definition'] for x in pool if x['word'] != target['word']]
        distractors = random.sample(all_defs, min(3, len(all_defs)))
        options = distractors + [target['definition']]
        random.shuffle(options)
        st.session_state.mc_q_data = {"target": target, "options": options, "answered": False, "choice": None}

    q = st.session_state.mc_q_data
    st.markdown(f"### 單字：**{q['target']['word']}**")
    
    for idx, opt in enumerate(q['options']):
        if st.button(opt, key=f"mc_{idx}", use_container_width=True, disabled=q['answered']):
            st.session_state.mc_q_data['answered'] = True
            st.session_state.mc_q_data['choice'] = opt
            if opt == q['target']['definition']: speak(q['target']['word'])
            st.rerun()

    if q['answered']:
        if q['choice'] == q['target']['definition']: st.success("正確！")
        else: st.error(f"錯誤，正確定義是：{q['target']['definition']}")
        st.info(f" **構造：** `{q['target']['breakdown']}`")
        if st.button("下一題 ➡️"):
            st.session_state.mc_q_data = None
            st.rerun()

def render_cloze_test_mode(pool):
    pool_with_ex = [x for x in pool if x.get('example') and x['word'].lower() in x['example'].lower()]
    if not pool_with_ex:
        st.warning("此分類例句不足。")
        return

    if 'cloze_q' not in st.session_state or st.session_state.cloze_q is None:
        target = random.choice(pool_with_ex)
        display_ex = re.compile(re.escape(target['word']), re.IGNORECASE).sub(" ________ ", target['example'])
        others = [x['word'] for x in pool if x['word'] != target['word']]
        distractors = random.sample(others, min(2, len(others)))
        options = distractors + [target['word']]
        random.shuffle(options)
        st.session_state.cloze_q = {"target": target, "display": display_ex, "options": options, "answered": False}

    q = st.session_state.cloze_q
    st.markdown(f" **{q['display']}** ")
    st.caption(f"👉 {q['target']['translation']}")

    for idx, opt in enumerate(q['options']):
        if st.button(opt, key=f"cl_{idx}", use_container_width=True, disabled=q['answered']):
            st.session_state.cloze_q['answered'] = True
            st.session_state.cloze_q['user_choice'] = opt
            if opt == q['target']['word']: speak(opt)
            st.rerun()

    if q['answered']:
        if q['user_choice'] == q['target']['word']: st.success("正確！")
        else: st.error(f"錯誤，答案是：{q['target']['word']}")
        if st.button("下一題 ➡️"):
            st.session_state.cloze_q = None
            st.rerun()

# --- C. 搜尋與列表區 (Search Page) ---
def ui_search_page(data, selected_cat):
    """整合後的搜尋頁面：包含隨機推薦與列表搜尋"""
    st.markdown('<h1 class="responsive-title">搜尋與瀏覽</h1>', unsafe_allow_html=True)
    
    # 搜尋輸入
    query = st.text_input("在選定領域中搜尋...", placeholder="輸入關鍵字如：act, bio...", key="root_search_bar").strip().lower()

    if selected_cat == "請選擇領域":
        st.warning("👈 **請從左側側邊欄的「分類篩選」選擇一個領域以展開列表。**")
        ui_newbie_whiteboard()
        return

    # 1. 如果沒有輸入搜尋詞，顯示隨機單字卡 (Hero Card)
    if not query:
        st.markdown("### 🎲 每日隨機推薦")
        all_words_in_cat = [v for c in data if c['category'] == selected_cat for g in c['root_groups'] for v in g['vocabulary']]
        if all_words_in_cat:
            q = random.choice(all_words_in_cat)
            st.markdown(f"""
                <div style="
                    background: var(--secondary-background-color);
                    border: 2px solid var(--primary-color);
                    border-radius: 20px;
                    padding: 2rem;
                    text-align: center;
                    margin-bottom: 2rem;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                ">
                    <div class="responsive-word" style="color: var(--primary-color); margin: 15px 0; font-weight:800;">{q['word']}</div>
                    <div style="margin-bottom: 15px;">
                        <span class="breakdown-container" style="font-size: 1.2rem; padding: 5px 15px;">{q['breakdown']}</span>
                    </div>
                    <div class="responsive-text" style="font-weight: bold; color: var(--text-color);">{q['definition']}</div>
                </div>
            """, unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            if c1.button("🔊 播放發音", use_container_width=True): speak(q['word'])
            if c2.button("🔄 換一張", use_container_width=True): st.rerun()
            st.divider()

    # 2. 顯示搜尋結果或完整列表
    relevant_cats = [c for c in data if c['category'] == selected_cat]
    found_any = False
    
    for cat in relevant_cats:
        for group in cat.get('root_groups', []):
            root_text = "/".join(group['roots']).lower()
            meaning_text = group['meaning'].lower()
            
            # 搜尋邏輯：若 query 為空則顯示所有，否則進行過濾
            matched_vocab = [
                v for v in group.get('vocabulary', [])
                if not query or (query in v['word'].lower() or query in root_text or query in meaning_text)
            ]
            
            if matched_vocab:
                found_any = True
                root_label = f"{root_text} ({group['meaning']})"
                # 若有搜尋，預設展開；若無搜尋(瀏覽模式)，預設摺疊
                is_expanded = True if query else False
                
                with st.expander(root_label, expanded=is_expanded):
                    for v in matched_vocab:
                        st.markdown(f'**{v["word"]}** `{v["breakdown"]}`: {v["definition"]}')
                        if st.button("播放", key=f"list_p_{v['word']}_{unique_key_gen()}"):
                            speak(v['word'])

    if not found_any and query:
        st.info(f"在「{selected_cat}」分類中找不到與「{query}」相關的結果。")

def unique_key_gen():
    """產生隨機 Key 避免 Streamlit 元件衝突"""
    return f"{int(time.time()*1000)}_{random.randint(0,9999)}"

# --- D. 管理員後台 (Admin Page) ---
def ui_admin_page(data):
    st.title("管制區")
    correct_password = st.secrets.get("admin_password", "8787")
    
    if not st.session_state.get('admin_auth'):
        pw_input = st.text_input("管理員密碼", type="password")
        if pw_input == correct_password:
            st.session_state.admin_auth = True
            st.rerun()
        elif pw_input != "": st.error("密碼錯誤")
        return

    # 管理功能
    st.metric("資料庫單字總量", f"{get_stats(data)[1]} 單字")
    
    if st.button("手動備份 CSV"):
        flat = [{"category": c['category'], "roots": "/".join(g['roots']), "meaning": g['meaning'], **v} 
                for c in data for g in c['root_groups'] for v in g['vocabulary']]
        st.download_button("確認下載 CSV", pd.DataFrame(flat).to_csv(index=False).encode('utf-8-sig'), "etymon_backup.csv")
    
    st.divider()
    st.subheader("雲端待處理回報")
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_pending = conn.read(spreadsheet=FEEDBACK_URL)
        if not df_pending.empty:
            st.dataframe(df_pending, use_container_width=True)
            if st.button("重新整理雲端數據"): st.rerun()
        else: st.info("目前沒有待處理的回報。")
    except Exception as e: st.error(f"讀取雲端回報失敗: {e}")

    if st.sidebar.button("登出管理區"):
        st.session_state.admin_auth = False
        st.rerun()

# ==========================================
# 5. 主程式入口 (Main Execution)
# ==========================================
def main():
    inject_custom_css()
    
    # 資料讀取
    with st.spinner("正在連線至字源資料庫..."):
        data = load_db()
    
    if not data:
        st.error("無法讀取資料，請檢查網路連線或 Google Sheet 設定。")
        return

    # 側邊欄導航
    with st.sidebar:
        st.title("🧩 Etymon Decoder")
        page = st.radio("功能選單", ["📚 字根學習區", "🔍 搜尋與瀏覽", "📝 測驗中心", "🔧 後台管理"])
        
        st.divider()
        
        # 取得所有分類供篩選
        categories = sorted(list(set(d['category'] for d in data)))
        selected_cat = st.selectbox("📂 分類篩選", ["請選擇領域"] + categories, index=0)
        
        # 統計資訊
        cat_count, word_count = get_stats(data)
        st.markdown(f"<div class='stats-container'>已收錄 <b>{cat_count}</b> 個領域<br>共 <b>{word_count}</b> 個單字</div>", unsafe_allow_html=True)
        
        # 音樂元件
        ui_time_based_lofi()

    # 頁面路由
    if page == "📚 字根學習區":
        if selected_cat == "請選擇領域":
            ui_newbie_whiteboard()
        else:
            ui_domain_page(
                [d for d in data if d['category'] == selected_cat],
                title=f"{selected_cat} - 字根拆解",
                theme_color="#FF4B4B",
                bg_color="#FF4B4B"
            )

    elif page == "🔍 搜尋與瀏覽":
        # 如果使用者在側邊欄選了 "請選擇領域"，預設顯示全部資料供搜尋，或提示使用者選擇
        # 這裡為了方便搜尋，若未選分類則視為搜尋全部，但在 ui_search_page 內部已有處理邏輯
        display_cat = selected_cat if selected_cat != "請選擇領域" else "請選擇領域"
        ui_search_page(data, display_cat)

    elif page == "📝 測驗中心":
        target_cat = selected_cat if selected_cat != "請選擇領域" else "全部顯示"
        ui_quiz_page(data, target_cat)

    elif page == "🔧 後台管理":
        ui_admin_page(data)

if __name__ == "__main__":
    main()
