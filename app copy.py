import datetime
import streamlit as st
import json
import os
import time
import random
import pandas as pd
import base64
from io import BytesIO
from gtts import gTTS
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 新增：全域自適應 CSS (只新增不刪減功能)
# ==========================================
def inject_custom_css():
    st.markdown("""
        <style>
            /* 1. 基礎字體比例加大 */
            html { font-size: 20px; } /* 整體基準點從 16px 提升 */

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

            /* 4. 構造拆解框：完全隨系統變色，不再寫死深色 */
            .breakdown-container {
                font-family: 'Courier New', monospace;
                font-weight: bold;
                background-color: var(--secondary-background-color); 
                color: var(--text-color); 
                padding: 12px 20px;
                border-radius: 12px;
                border: 2px solid var(--primary-color); /* 用主題色框出重點 */
                display: inline-block;
                margin: 10px 0;
            }

            /* 5. 側邊欄統計框：隨系統變色 */
            .stats-container {
                text-align: center; 
                padding: 20px; 
                background-color: var(--secondary-background-color); 
                border: 1px solid rgba(128, 128, 128, 0.2);
                border-radius: 15px; 
                color: var(--text-color);
            }

            /* 6. 禁止 Selectbox 輸入並加強 Pill 按鈕視覺 */
            .stSelectbox div[role="button"] input { caret-color: transparent !important; pointer-events: none !important; }
            
            div[data-testid="stPills"] button {
                font-size: 1.1rem !important;
                padding: 8px 16px !important;
            }
        </style>
    """, unsafe_allow_html=True)
# ==========================================
# 1. 修正語音發音 (改良為 HTML5 標籤)
# ==========================================
def speak(text):
    """終極修正版：使用 JavaScript 強制觸發瀏覽器音訊播放"""
    try:
        import time
        tts = gTTS(text=text, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        audio_base64 = base64.b64encode(fp.read()).decode()
        
        # 產生唯一 ID 避免快取衝突
        unique_id = f"audio_{int(time.time() * 1000)}"
        
        # 使用 JavaScript 建立音訊物件並播放
        # 這能繞過 HTML 標籤不更新的問題，並強制瀏覽器執行播放指令
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

# ==========================================
# 1. 核心配置與雲端同步 (保留原代碼)
# ==========================================
SHEET_ID = '1W1ADPyf5gtGdpIEwkxBEsaJ0bksYldf4AugoXnq6Zvg'
GSHEET_URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv'
PENDING_FILE = 'pending_data.json'
FEEDBACK_URL = st.secrets.get("feedback_sheet_url")

@st.cache_data(ttl=600)
def load_db():
    # 定義 9 欄一組的範圍
    BLOCKS = ["A:I", "J:R", "S:AA", "AB:AJ", "AK:AS"]
    COL_NAMES = [
        'category', 'roots', 'meaning', 'word', 
        'breakdown', 'definition', 'phonetic', 'example', 'translation'
    ]
    
    all_dfs = []
    for rng in BLOCKS:
        try:
            url = f"{GSHEET_URL}&range={rng}"
            # 重點：使用 skiprows=1 避開標題列，並手動指定欄位名稱
            df_part = pd.read_csv(url, skiprows=1, names=COL_NAMES)
            
            # 清理資料：移除全空的列，並確保 category 欄位有值
            df_part = df_part.dropna(subset=['category', 'word'], how='all')
            
            if not df_part.empty:
                all_dfs.append(df_part)
        except Exception as e:
            continue

    if not all_dfs: return []
    df = pd.concat(all_dfs, ignore_index=True)
    
    # 結構化處理
    structured_data = []
    # 移除可能重複讀入標題字串的異常資料 (保險機制)
    df = df[df['category'] != 'category'] 
    
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
def ui_time_based_lofi():
    """
    四個時段自動切換 (06-12, 12-18, 18-23, 23-06)
    使用 Lofi Girl 官方最穩定的嵌入 ID
    """
    # 1. 取得台灣時間 (UTC+8)
    utc_now = datetime.datetime.utcnow()
    tw_now = utc_now + datetime.timedelta(hours=8)
    hour = tw_now.hour

    # 2. 設定四個時段的影片 ID (使用官方長期直播 ID)
    # jfKfPfyJRdk: Study/Relax (經典書桌女孩)
    # 28KRPhVzCus: Sleep/Chill (深夜女孩)
    if 6 <= hour < 12:
        mode_name = "☀️ 晨間能量 (Morning)"
        video_id = "jfKfPfyJRdk" 
        icon = "🌅"
    elif 12 <= hour < 18:
        mode_name = "☕ 午後專注 (Study)"
        video_id = "jfKfPfyJRdk" 
        icon = "📖"
    elif 18 <= hour < 23:
        mode_name = "🌆 晚間複習 (Chill)"
        video_id = "28KRPhVzCus" # 切換到更安靜的睡眠頻道
        icon = "🛋️"
    else:
        # 23:00 - 06:00
        mode_name = "🌙 深夜療癒 (Sleep)"
        video_id = "28KRPhVzCus"
        icon = "😴"

    with st.sidebar.expander(f"🎵 時光音樂：{mode_name}", expanded=True):
        st.write(f"🕒 台灣時間：{tw_now.strftime('%H:%M')}")
        
        # 這裡使用最穩定的嵌入參數
        # playsinline=1: iPhone 網頁內播放
        # rel=0: 結束後不顯示相關影片
        embed_code = f"""
            <div style="border-radius:12px; overflow:hidden; border: 1px solid #ddd; background: #000;">
                <iframe width="100%" height="200" 
                    src="https://www.youtube.com/embed/{video_id}?rel=0&modestbranding=1&playsinline=1&autoplay=0" 
                    frameborder="0" 
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                    allowfullscreen>
                </iframe>
            </div>
        """
        st.markdown(embed_code, unsafe_allow_html=True)
        st.caption(f"目前處於 {icon} 時段。若顯示無法播放，請點擊影片標題開啟。")
def save_feedback_to_gsheet(word, feedback_type, comment):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=FEEDBACK_URL, ttl=0)
        new_row = pd.DataFrame([{
            "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "word": word, "type": feedback_type, "comment": comment, "status": "pending"
        }])
        updated_df = pd.concat([df, new_row], ignore_index=True)
        conn.update(spreadsheet=FEEDBACK_URL, data=updated_df)
        st.success(f"✅ 單字「{word}」的回報已同步至雲端！")
    except Exception as e:
        st.error(f"❌ 雲端同步失敗。")
        st.caption(f"錯誤詳情: {e}")

def get_stats(data):
    if not data: return 0, 0
    total_words = sum(len(g.get('vocabulary', [])) for cat in data for g in cat.get('root_groups', []))
    return len(data), total_words

# ==========================================
# 2. 通用與專業區域組件 (調整為自適應樣式)
# ==========================================
def ui_domain_page(domain_data, title, theme_color, bg_color):
    # --- 任務 1：使用說明介面 ---
    with st.expander("📖 初次使用？點擊查看「拆解式學習法」說明", expanded=False):
        st.markdown(f"""
        <div style="padding:15px; border-radius:10px; background-color:{bg_color}22; border-left:5px solid {theme_color};">
            <h4 style="color:{theme_color}; margin-top:0;">如何使用此工具？</h4>
            <ol class="responsive-text">
                <li><b>搜尋字根：</b> 在下方輸入框輸入你想找的字根（如 <code>bio</code>）或含義（如 <code>生命</code>）。</li>
                <li><b>觀察構造：</b> 點開單字後，重點看「構造拆解」，理解前綴、字根、後綴如何組合成新字。</li>
                <li><b>聽音記憶：</b> 點擊「播放」按鈕，結合發音與拆解能大幅提升記憶深度。</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f'<h1 class="responsive-title">{title}</h1>', unsafe_allow_html=True)
    
    # 建立字根映射表
    root_map = {}
    for cat in domain_data:
        for group in cat.get('root_groups', []):
            label = f"{'/'.join(group['roots'])} ({group['meaning']})"
            root_map[label] = group
    
    # --- 任務 2：刪除按鈕，改為輸入搜尋框 ---
    search_query = st.text_input("輸入字根或含義進行篩選", placeholder="例如：act, bio, 動作, 生命...")
    
    # 根據輸入內容篩選字根
    filtered_labels = [
        label for label in root_map.keys() 
        if search_query.lower() in label.lower()
    ]

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
        st.caption("請在上方輸入框輸入字根開始探索。")
def ui_feedback_component(word):
    with st.popover("錯誤回報"):
        st.write(f"回報單字：**{word}**")
        f_type = st.selectbox("錯誤類型", ["發音錯誤(手機平板暫無發音)", "拆解有誤", "中文釋義錯誤", "分類錯誤", "其他"], key=f"err_type_{word}")
        f_comment = st.text_area("詳細說明", placeholder="請描述正確的資訊...", key=f"err_note_{word}")
        if st.button("提交回報", key=f"err_btn_{word}"):
            if f_comment.strip() == "": st.error("請填寫說明內容")
            else:
                save_feedback_to_gsheet(word, f_type, f_comment)
                st.success("感謝回報！")
def ui_newbie_whiteboard():
    st.markdown("""
    <div style="background-color: var(--secondary-background-color); padding: 25px; border-radius: 15px; border: 2px dashed var(--primary-color);">
        <h2 style="margin-top:0; text-align:center;">歡迎使用 Etymon Decoder</h2>
        <p style="text-align:center; opacity:0.8;">這是一個專為「拆解式學習」設計的工具，幫你從根本理解英文。</p>
        <hr>
        <h4 style="color:var(--primary-color);">1. 核心邏輯：拆解積木</h4>
        <p>英文單字是由積木組成的。例如：<b>Re (回) + Port (搬運) = Report (報告)</b>。</p>
    """, unsafe_allow_html=True)

    # 此處建議放入您提供的圖片 (例如單字結構圖)
    # st.image("path_to_your_image.png", caption="單字結構示範")
    

    st.markdown("""
        <h4 style="color:var(--primary-color);">2. 快速上手步驟</h4>
        <ul class="responsive-text">
            <li><b>第一步：鎖定領域</b> - 從左側選單選擇適合你的程度（如：國中區）。</li>
            <li><b>第二步：精準搜尋</b> - 在搜尋框輸入字根 (如 <code>bio</code>) 或含義 (如 <code>生命</code>)。</li>
            <li><b>第三步：聽音看拆解</b> - 點開結果，觀看拆解公式並點擊播放聆聽發音。</li>
        </ul>
        <h4 style="color:var(--primary-color);">3. 找不到想搜尋的？</h4>
        <p>往左上角看！側邊欄有<b>「分類篩選」</b>，可以快速瀏覽特定學科的單字庫。</p>
    </div>
    """, unsafe_allow_html=True)
def ui_quiz_page(data, selected_cat_from_sidebar):
    st.markdown('<div class="responsive-title" style="font-weight:bold;">學習測驗區 (Flashcards)</div>', unsafe_allow_html=True)

    # 1. 檢查側邊欄是否有選擇領域
    if selected_cat_from_sidebar == "請選擇領域":
        st.warning("👈 **請先從左側「分類篩選」選擇一個領域（或『全部顯示』）來開始測驗！**")
        return

    # 2. 自動偵測側邊欄切換，若分類改變則清空目前題目
    if st.session_state.get('last_quiz_cat') != selected_cat_from_sidebar:
        st.session_state.last_quiz_cat = selected_cat_from_sidebar
        if 'flash_q' in st.session_state: 
            del st.session_state.flash_q
        st.rerun()

    # 3. 根據側邊欄選擇建立題目池
    if 'flash_q' not in st.session_state:
        if selected_cat_from_sidebar == "全部顯示":
            pool = [{**v, "cat": c['category']} for c in data for g in c['root_groups'] for v in g['vocabulary']]
        else:
            pool = [{**v, "cat": c['category']} for c in data if c['category'] == selected_cat_from_sidebar for g in c['root_groups'] for v in g['vocabulary']]
        
        if not pool: 
            st.warning("此範圍無資料")
            return
            
        st.session_state.flash_q = random.choice(pool)
        st.session_state.flipped = False
        st.session_state.voiced = False 

    # 4. 顯示目前題目
    q = st.session_state.flash_q
    
    # 顯示目前測驗範圍提醒
    st.caption(f"📍 目前範圍：{selected_cat_from_sidebar}")
    
    # 單字卡片
    st.markdown(f"""
        <div style="text-align: center; padding: 5vh 2vw; border: 3px solid #eee; border-radius: 25px; background: #fdfdfd; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <p style="color: #999; font-weight: bold;">[ {q['cat']} ]</p>
            <h1 class="responsive-word" style="margin: 0; color: #1E88E5;">{q['word']}</h1>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("查看答案", use_container_width=True): st.session_state.flipped = True
    with col2:
        if st.button("播放發音", use_container_width=True): speak(q['word'])
    with col3:
        if st.button("➡️ 下一題", use_container_width=True): 
            if 'flash_q' in st.session_state: del st.session_state.flash_q
            st.rerun()

    if st.session_state.get('flipped'):
        if not st.session_state.get('voiced'):
            speak(q['word'])
            st.session_state.voiced = True
        
        is_legal = "法律" in q['cat']
        bg_color, label_color, text_color, breakdown_color = ("#1A1A1A", "#FFD700", "#FFFFFF", "#FFD700") if is_legal else ("#E3F2FD", "#1E88E5", "#000000", "#D32F2F")
        p_val = str(q.get('phonetic', '')).strip().replace('/', '')
        phonetic_html = f"<div style='color:{label_color}; font-size:1.2em; margin-bottom:5px;'>/{p_val}/</div>" if p_val and p_val != "nan" else ""
        e_val, t_val = str(q.get('example', '')).strip(), str(q.get('translation', '')).strip()
        example_html = f"<hr style='border-color:#555; margin:15px 0;'><div style='font-style:italic; color:#666;' class='responsive-text'>{e_val}</div>" if e_val and e_val != "nan" else ""
        if t_val and t_val != "nan": example_html += f"<div style='color:#666; font-size:0.95em; margin-top:5px;'>({t_val})</div>"

        st.markdown(f"""
            <div style="background-color:{bg_color}; padding:25px; border-radius:15px; border-left:10px solid {label_color}; margin-top:20px;">
                {phonetic_html}
                <div class="responsive-text" style="color:{text_color};">
                    <strong style="color:{label_color};">拆解：</strong>
                    <span style="color:{breakdown_color}; font-family:monospace; font-weight:bold;">{q['breakdown']}</span>
                </div>
                <div class="responsive-text" style="color:{text_color}; margin-top:10px;">
                    <strong style="color:{label_color};">釋義：</strong> {q['definition']}
                </div>
                {example_html}
            </div>
        """, unsafe_allow_html=True)
def ui_search_page(data, selected_cat):
    # --- 任務 1：標題與教學按鈕 ---
    col_title, col_help = st.columns([3, 1])
    with col_title:
        st.markdown('<h1 class="responsive-title">搜尋與瀏覽</h1>', unsafe_allow_html=True)
    with col_help:
        # 命名為教學區的按鈕
        with st.popover("📖 教學區", use_container_width=True):
            ui_newbie_whiteboard() 

    # --- 任務 2：搜尋引導 ---
    st.markdown("### 🔍 快速搜尋")
    query = st.text_input(
        "第一步：輸入字根或含義", 
        placeholder="例如：act, bio...", 
        key="global_search_input"
    ).strip().lower()
    
    # 判斷是否滿足顯示條件
    if not query:
        st.info("💡 提示：請先在上方輸入框輸入關鍵字。")
        ui_newbie_whiteboard() # 顯示新手白板
        return

    if selected_cat == "全部顯示":
        st.warning("請從側邊欄「分類篩選」選擇一個特定的領域（如：國小基礎）以顯示列表。")
        return

    # --- 執行列表顯示 ---
    relevant = [c for c in data if c['category'] == selected_cat]
    found_results = False
    
    for cat in relevant:
        for group in cat.get('root_groups', []):
            matched_vocab = [
                v for v in group['vocabulary'] 
                if query in v['word'].lower() or any(query in r.lower() for r in group['roots'])
            ]
            
            if matched_vocab:
                found_results = True
                root_label = f"{'/'.join(group['roots'])} ({group['meaning']})"
                with st.expander(f"✨ {root_label}", expanded=True):
                    for v in matched_vocab:
                        st.markdown(f'**{v["word"]}** `{v["breakdown"]}`: {v["definition"]}')
                        if st.button("播放", key=f"p_{v['word']}"): speak(v['word'])
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
    st.metric("資料庫單字總量", f"{get_stats(data)[1]} 單字")
    if st.button("手動備份 CSV"):
        flat = [{"category": c['category'], "roots": "/".join(g['roots']), "meaning": g['meaning'], **v} for c in data for g in c['root_groups'] for v in g['vocabulary']]
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
def ui_search_page_all_list(data, selected_cat):
    st.markdown('<h1 class="responsive-title">搜尋與瀏覽</h1>', unsafe_allow_html=True)
    
    # 醒目提醒：篩選與導航的關聯
    if selected_cat == "全部顯示":
        st.warning("👈 **請注意：查看列表前，請先確保左側「導航」處於『字根區』，並從下方「分類篩選」選擇一個領域（如：國小基礎）。**")
        st.info("💡 系統預設不會顯示所有內容，以避免介面過於混亂。")
        ui_newbie_whiteboard() # 顯示新手教學引導
        return
    # 搜尋框：維持在列表上方
    query = st.text_input("搜尋單字或字根...", placeholder="例如：act, bio, 動作...", key="root_search_bar").strip().lower()

    # 門檻判斷：必須選取分類
    if selected_cat == "全部顯示":
        st.warning("⚠️ 請從左側選單的『分類篩選』選擇一個特定的領域（例如：國小基礎）以展開完整列表。")
        ui_newbie_whiteboard() # 提示新手教學
        return

    # 滿足條件：執行過濾並「全部列出」
    # 如果 query 為空，matched_vocab 就會包含該分類下的所有內容
    relevant_cats = [c for c in data if c['category'] == selected_cat]
    found_any = False
    
    for cat in relevant_cats:
        for group in cat.get('root_groups', []):
            root_text = "/".join(group['roots']).lower()
            meaning_text = group['meaning'].lower()
            
            # 過濾邏輯：如果沒有輸入搜尋，則顯示所有單字
            matched_vocab = [
                v for v in group.get('vocabulary', [])
                if not query or (query in v['word'].lower() or query in root_text or query in meaning_text)
            ]
            
            if matched_vocab:
                found_any = True
                root_label = f"{root_text} ({group['meaning']})"
                with st.expander(root_label, expanded=False): # 預設折疊，搜尋時可視情況展開
                    for v in matched_vocab:
                        st.markdown(f'**{v["word"]}** `{v["breakdown"]}`: {v["definition"]}')
                        if st.button("播放", key=f"search_p_{v['word']}_{root_text}"):
                            speak(v['word'])
    
    if not found_any and query:
        st.info(f"在「{selected_cat}」分類中找不到與「{query}」相關的結果。")
def ui_newbie_whiteboard_page():
    """任務 3：獨立的教學區白板頁面"""
    st.markdown('<h1 class="responsive-title">📖 教學區：如何解碼單字？</h1>', unsafe_allow_html=True)
    
    # 使用與 ui_newbie_whiteboard 類似的樣式但改為全頁面顯示
    st.markdown("""
    <div style="background-color: var(--secondary-background-color); padding: 30px; border-radius: 20px; border: 3px solid var(--primary-color);">
        <h3 style="color:var(--primary-color);">1. 核心邏輯：拆解積木</h3>
        <p class="responsive-text">英文單字不是死背字母，而是看懂組成。就像樂高一樣：</p>
        <div style="text-align: center; background: rgba(128,128,128,0.1); padding: 20px; border-radius: 15px; margin: 15px 0;">
            <span style="font-size: 1.5rem; font-weight: bold;">
                <span style="color: #D32F2F;">Pre</span> (前) + 
                <span style="color: #1E88E5;">dict</span> (說) = 
                <span style="color: var(--text-color);">Predict</span> (預測)
            </span>
        </div>
    """, unsafe_allow_html=True)

    # 插入單字構造圖 
    

    st.markdown("""
        <h3 style="color:var(--primary-color); margin-top:30px;">2. 字根區快速上手指南</h3>
        <div style="background: white; color: black; padding: 20px; border-radius: 10px; border: 1px solid #ddd;">
            <ul class="responsive-text">
                <li><b>Step 1：切換至「字根區」</b> - 點選左側導航選鈕。</li>
                <li><b>Step 2：輸入關鍵字</b> - 在中央搜尋框輸入字根（如 <code>bio</code>）或含義（如 <code>生命</code>）。</li>
                <li><b>Step 3：選取分類標籤</b> - <b>重要！</b>必須在左側側邊欄選擇一個領域（如：國中區、醫學區），列表才會出現。</li>
            </ul>
        </div>
        <p style="margin-top:20px; text-align:center; font-style:italic; opacity:0.8;">
            準備好了嗎？點選左側「字根區」開始解碼吧！
        </p>
    </div>
    """, unsafe_allow_html=True)

def display_filtered_results(data, query, selected_cat):
    """執行字根區的過濾顯示"""
    # 篩選特定類別的資料
    relevant_cats = [c for c in data if c['category'] == selected_cat]
    found_any = False
    
    for cat in relevant_cats:
        for group in cat.get('root_groups', []):
            # 檢查字根或含義是否符合搜尋
            root_text = "/".join(group['roots']).lower()
            meaning_text = group['meaning'].lower()
            
            # 同時過濾單字
            matched_vocab = [
                v for v in group.get('vocabulary', [])
                if query in v['word'].lower() or query in root_text or query in meaning_text
            ]
            
            if matched_vocab:
                found_any = True
                root_label = f"✨ {root_text.upper()} ({group['meaning']})"
                with st.expander(root_label, expanded=True):
                    for v in matched_vocab:
                        st.markdown(f'<div class="responsive-word" style="font-weight:bold; color:#1E88E5;">{v["word"]}</div>', unsafe_allow_html=True)
                        
                        col_play, _ = st.columns([1, 3])
                        with col_play:
                            if st.button("播放發音", key=f"search_p_{v['word']}"):
                                speak(v['word'])
                        
                        st.markdown(f"""
                            <div class="breakdown-container responsive-breakdown">{v['breakdown']}</div>
                            <div class="responsive-text"><b>定義：</b>{v['definition']}</div>
                            <hr style="opacity:0.1;">
                        """, unsafe_allow_html=True)
    
    if not found_any:
        st.info(f"在「{selected_cat}」分類中找不到關於「{query}」的結果。")
# ==========================================
# 修正後的字根區：支援全部列出與搜尋
# ==========================================
def ui_search_page_all_list(data, selected_cat):
    st.markdown('<h1 class="responsive-title">搜尋與瀏覽</h1>', unsafe_allow_html=True)
    
    # 搜尋框
    query = st.text_input("在選定領域中搜尋...", placeholder="輸入關鍵字如：act, bio...", key="root_search_bar").strip().lower()

    if selected_cat == "請選擇領域":
        st.warning("👈 **請從左側側邊欄的「分類篩選」選擇一個領域以展開列表。**")
        ui_newbie_whiteboard() # 顯示教學引導
        return

    # 顯示過濾後的列表
    relevant_cats = [c for c in data if c['category'] == selected_cat]
    found_any = False
    
    for cat in relevant_cats:
        for group in cat.get('root_groups', []):
            root_text = "/".join(group['roots']).lower()
            meaning_text = group['meaning'].lower()
            
            # 搜尋邏輯：無 query 則全列
            matched_vocab = [
                v for v in group.get('vocabulary', [])
                if not query or (query in v['word'].lower() or query in root_text or query in meaning_text)
            ]
            
            # ... 前面程式碼不變 ...

            if matched_vocab:
                found_any = True
                root_label = f"{root_text.upper()} ({group['meaning']})"
                # 搜尋時自動展開，平時收合
                with st.expander(f"✨ {root_label}", expanded=True if query else False):
                    for v in matched_vocab:
                        # 1. 顯示單字資訊
                        st.markdown(f'**{v["word"]}** `{v["breakdown"]}`: {v["definition"]}')
                        
                        # 2. 建立按鈕橫列 (把播放和報錯放在一起比較美觀)
                        col1, col2 = st.columns([1, 4])
                        with col1:
                            if st.button("播放", key=f"p_{v['word']}_{root_text}"): 
                                speak(v['word'])
                        with col2:
                            # --- 在這裡呼叫你的報錯組件 ---
                            ui_feedback_component(v["word"])
                        
                        st.write("") # 增加一點間距
def ui_newbie_whiteboard_page():
    st.markdown('<h1 class="responsive-title">📖 教學區</h1>', unsafe_allow_html=True)
    
    st.success("### 🔍 如何正確搜尋與瀏覽？")
    st.markdown("""
     使用本工具時，請遵循以下步驟以獲得最佳體驗：
    * **步驟一：** 在左側選單點選你想查看的程度（如：高中區）。
    * **步驟二：** 在下方功能區點選想要的功能如 **「字根區」**  。
    * **步驟三：** 此時右側會出現 **「搜尋框」**，可以輸入關鍵字進行精確篩選。
    * 
    * **提示一：** **「學習區」** 可以依據 **程度** 或是 **全部** 來決定題目字卡的範圍
    * **提示二：手機/平板在選單右邊多點幾下就可以關閉選單了！**
    * **提示三：** 在選單左上方新增四個時間段（06-12, 12-18, 18-23, 23-06）的音樂 **（可能不穩定）**
    """)
    
    st.divider()
    ui_newbie_whiteboard() # 原有的拆解教學內容
# ==========================================
# 3. 主程序入口
# ==========================================
def main():
    st.set_page_config(page_title="Etymon Decoder", layout="wide")
    inject_custom_css()
    data = load_db()
    
    st.sidebar.title("Etymon Decoder")
    ui_time_based_lofi() 
    # ==========================================
    # 1. 搬移上來的功能：統計、刷新與分類篩選
    # ==========================================
    with st.sidebar.container():
        # 顯示資料庫統計
        _, total_words = get_stats(data)
        st.markdown(f"""
            <div class="stats-container" style="margin-bottom: 10px;">
                <small>資料庫總計</small><br>
                <span style="font-size: 1.8rem; font-weight: bold; color: #1E88E5;">{total_words}</span> 
                <span style="font-size: 1rem; opacity: 0.8;">Words</span>
            </div>
        """, unsafe_allow_html=True)
        
        # 強制刷新按鈕
        if st.button("🔄 強制刷新雲端數據", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.sidebar.divider()

    # 分類篩選：現在是控制資料顯示的核心
    st.sidebar.markdown("### 1. 選擇領域 (分類篩選)")
    all_cats = sorted(list(set(c['category'] for c in data)))
    cats = ["請選擇領域", "全部顯示"] + all_cats # 這裡新增了全部顯示
    selected_cat = st.sidebar.radio("1. 選擇領域：", cats, key="filter_cat")
    
    st.sidebar.divider()

    # ==========================================
    # 2. 導航選單：僅保留教學區、字根區、學習區
    # ==========================================
    st.sidebar.markdown("### 2. 切換功能")
    menu = st.sidebar.radio(
        "功能導航：", 
        ["教學區", "字根區", "學習區"],
        key="main_nav"
    )

    # 操作提醒
    st.sidebar.info("💡 **操作提醒：**\n欲查看單字列表，請務必先點選「字根區」，再從上方「分類篩選」選取領域。")

    # ==========================================
    # 3. 主內容路由邏輯
    # ==========================================
    if menu == "教學區":
        ui_newbie_whiteboard_page() 
        
    elif menu == "字根區":
        # 呼叫整合了「全部列出」與「搜尋」的功能
        ui_search_page_all_list(data, selected_cat)
        
    # ... 在 main() 的路由邏輯中 ...
    elif menu == "學習區":
        # 傳入選定的領域，讓習題與篩選連動
        ui_quiz_page(data, selected_cat)
# 確保在檔案最下方呼叫
if __name__ == "__main__":
    main()
