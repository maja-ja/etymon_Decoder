import streamlit as st
import pandas as pd
import base64
import time
import random
from io import BytesIO
from gtts import gTTS

# ==========================================
# 1. 核心配置與 CSS (Config & CSS)
# ==========================================
st.set_page_config(
    page_title="Etymon Decoder",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Google Sheet 設定 (維持您原本的設定)
SHEET_ID = '1W1ADPyf5gtGdpIEwkxBEsaJ0bksYldf4AugoXnq6Zvg'
GSHEET_URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv'

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
                margin-top: 20px;
            }
            .stSelectbox div[role="button"] input { caret-color: transparent !important; pointer-events: none !important; }
            div[data-testid="stPills"] button { font-size: 1.1rem !important; padding: 8px 16px !important; }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 工具函式 (Utils)
# ==========================================

def speak(text, key_suffix=""):
    """
    使用 JavaScript 強制觸發瀏覽器音訊播放，解決自動播放限制。
    """
    try:
        if not text or pd.isna(text):
            return
            
        tts = gTTS(text=text, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        audio_base64 = base64.b64encode(fp.read()).decode()
        
        # 產生唯一的 ID 以避免衝突
        unique_id = f"audio_{int(time.time() * 1000)}_{random.randint(0,999)}_{key_suffix}"
        
        # 注入 JS 播放器
        audio_html = f"""
            <audio id="{unique_id}" autoplay="true" style="display:none;">
                <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
            </audio>
            <script>
                (function() {{
                    var audio = document.getElementById("{unique_id}");
                    if (audio) {{
                        audio.play().catch(function(error) {{
                            console.log("Autoplay blocked, waiting for interaction.");
                        }});
                    }}
                }})();
            </script>
        """
        st.components.v1.html(audio_html, height=0)
    except Exception as e:
        st.error(f"語音生成失敗: {e}")

# 學習網站的 load_db
@st.cache_data(ttl=10)
def load_db():
    # 這裡現在是 10 欄一組
    COL_NAMES = ['category', 'roots', 'meaning', 'word', 'breakdown', 'definition', 'phonetic', 'example', 'translation', 'native_vibe']
    # 範圍從 A:I 延伸到 A:J
    BLOCKS = ["A:J", "K:T", "U:AD", "AE:AN", "AO:AX"] 
    # ... 其餘讀取邏輯不變= ['category', 'roots', 'meaning', 'word', 'breakdown', 'definition', 'phonetic', 'example', 'translation']
    
    all_dfs = []
    for rng in BLOCKS:
        try:
            url = f"{GSHEET_URL}&range={rng}"
            # 讀取 CSV
            df_part = pd.read_csv(url, skiprows=1, names=COL_NAMES)
            # 清理：移除完全空白的列，或關鍵欄位為空的列
            df_part = df_part.dropna(subset=['category', 'word'], how='any')
            
            if not df_part.empty:
                # 簡單的資料清理
                df_part['word'] = df_part['word'].astype(str).str.strip()
                df_part['category'] = df_part['category'].astype(str).str.strip()
                all_dfs.append(df_part)
        except Exception as e:
            # 容錯：若某個區塊讀取失敗，跳過並記錄
            print(f"Error reading block {rng}: {e}")
            continue

    if not all_dfs:
        return pd.DataFrame(columns=COL_NAMES)
        
    final_df = pd.concat(all_dfs, ignore_index=True)
    return final_df.drop_duplicates(subset=['word'])

# ==========================================
# 3. 頁面邏輯 (Pages)
# ==========================================

def page_home(df):
    st.markdown("<h1 style='text-align: center;'>Etymon Decoder</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>透過字根字首，解碼英語單字的核心邏輯。</p>", unsafe_allow_html=True)
    st.write("---")
    
    # 統計數據
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""<div class="stats-box"><h2>{len(df)}</h2><p>總單字量</p></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="stats-box"><h2>{df['category'].nunique()}</h2><p>分類主題</p></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="stats-box"><h2>{df['roots'].nunique()}</h2><p>獨特字根</p></div>""", unsafe_allow_html=True)
    
    st.write("---")
    st.info("👈 請從左側選單選擇功能：\n\n* **學習與搜尋**：隨機單字卡或查詢特定單字。\n* **測驗模式**：測試您的字根記憶。")

def page_learn_search(df):
    """合併後的搜尋與學習頁面"""
    st.title("學習與搜尋")
    
    # 使用 Tabs 分流功能
    tab1, tab2 = st.tabs(["隨機單字卡", "資料庫列表"])
    
   # --- TAB 1: 隨機單字卡 ---
    with tab1:
        c1, c2 = st.columns([3, 1])
        with c1:
            categories = ["全部"] + sorted(df['category'].unique().tolist())
            selected_cat = st.selectbox("選擇分類 (Topic)", categories)
        
        # 過濾資料
        if selected_cat == "全部":
            filtered_df = df
        else:
            filtered_df = df[df['category'] == selected_cat]
            
        if filtered_df.empty:
            st.warning("此分類暫無資料。")
        else:
            # 1. 初始化與重置狀態 (新增 vibe_unlocked 追蹤)
            if 'current_word' not in st.session_state:
                st.session_state.current_word = filtered_df.sample(1).iloc[0].to_dict()
                st.session_state.vibe_unlocked = False # 初始未解鎖

            # 2. 抽卡按鈕 (點擊時重置解鎖狀態)
            if st.button("下一個單字 (Next Word)", use_container_width=True, type="primary"):
                st.session_state.current_word = filtered_df.sample(1).iloc[0].to_dict()
                st.session_state.vibe_unlocked = False # 重置解鎖狀態
                st.session_state.pop('audio_trigger', None)
                st.rerun() # 確保畫面立即更新
            
            # 顯示卡片內容
            word_data = st.session_state.current_word
            
            st.write("---")
            # 單字與發音
            st.markdown(f"<div class='responsive-word' style='text-align:center;'>{word_data.get('word', '')}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='responsive-phonetic' style='text-align:center;'>{word_data.get('phonetic', '')}</div>", unsafe_allow_html=True)
            
            # 發音按鈕
            col_audio, col_empty = st.columns([1, 4])
            with col_audio:
                if st.button("發音"):
                    speak(word_data.get('word'), key_suffix="card")

            # 拆解區
            st.markdown(f"""
                <div class='breakdown-container'>
                    <div class='responsive-breakdown'>{word_data.get('breakdown', 'No breakdown')}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # 釋義與例句
            st.markdown(f"### {word_data.get('definition', '')}")
            st.info(f" **Roots:** {word_data.get('roots', '')} = {word_data.get('meaning', '')}")
            
            # --- 🎁 語感驚喜包邏輯 (關鍵更新) ---
            native_vibe = word_data.get('native_vibe')
            if pd.notna(native_vibe) and native_vibe != "":
                st.write("") # 增加間距
                
                # 如果尚未解鎖
                if not st.session_state.get('vibe_unlocked', False):
                    st.markdown("""
                        <div style="text-align: center; padding: 25px; border: 2px dashed #6c5ce7; border-radius: 15px; background-color: #f8f9fa; margin: 10px 0;">
                            <h4 style="color: #6c5ce7; margin: 0;">🎁 獲得一個語感驚喜包！</h4>
                            <p style="font-size: 0.9rem; color: #666;">點擊下方按鈕拆封母語人士的直覺...</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button("✨ 立即拆封 (Unlock Vibe)", use_container_width=True):
                        st.session_state.vibe_unlocked = True
                        st.balloons() # 撒花慶祝！
                        st.rerun()
                
                # 如果已經解鎖，顯示內容
                else:
                    st.markdown(f"""
                        <div style="background-color: #f0f2f6; padding: 20px; border-radius: 15px; border-left: 8px solid #6c5ce7; position: relative; animation: fadeIn 0.8s;">
                            <p style="color: #6c5ce7; font-weight: bold; margin-bottom: 8px; font-size: 1.1rem;">🧠 母語人士語感 (Native Vibe):</p>
                            <div style="font-style: italic; color: #2d3436; line-height: 1.6; font-size: 1.05rem;">
                                {native_vibe}
                            </div>
                            <div style="text-align: right; font-size: 0.7rem; color: #6c5ce7; margin-top: 10px;">✨ 已解鎖的神經直覺</div>
                        </div>
                        <style>
                            @keyframes fadeIn {{
                                from {{ opacity: 0; transform: translateY(10px); }}
                                to {{ opacity: 1; transform: translateY(0); }}
                            }}
                        </style>
                    """, unsafe_allow_html=True)

            # 顯示原本的例句 (放在驚喜包之後)
            if pd.notna(word_data.get('example')) and word_data.get('example') != "":
                st.write("")
                st.success(f"**Example:**\n{word_data.get('example', '')}\n\n*{word_data.get('translation', '')}*")
    # --- TAB 2: 搜尋列表 ---
    with tab2:
        search_query = st.text_input("輸入關鍵字 (英文或中文)...", placeholder="ex: love, phil, 顯微鏡")
        
        if search_query:
            # 多欄位模糊搜尋
            mask = (
                df['word'].str.contains(search_query, case=False, na=False) |
                df['roots'].str.contains(search_query, case=False, na=False) |
                df['definition'].str.contains(search_query, case=False, na=False) |
                df['translation'].str.contains(search_query, case=False, na=False)
            )
            results = df[mask]
            st.write(f"找到 {len(results)} 筆結果：")
            st.dataframe(results[['word', 'breakdown', 'definition', 'roots', 'category']], use_container_width=True)
        else:
            st.write("顯示前 20 筆資料：")
            st.dataframe(df[['word', 'breakdown', 'definition', 'roots', 'category']].head(20), use_container_width=True)

def page_quiz(df):
    """測驗模式 (含狀態防呆)"""
    st.title("字根測驗")

    # 1. 選擇範圍
    categories = list(df['category'].unique())
    selected_cat = st.selectbox("選擇測驗範圍", categories)

    # 2. 狀態管理初始化
    if 'quiz_state' not in st.session_state:
        st.session_state.quiz_state = {
            'active': False,
            'score': 0,
            'total': 0,
            'category': None,
            'current_q': None,
            'show_answer': False
        }

    # 3. 防呆：如果切換了類別，重置測驗
    if st.session_state.quiz_state['category'] != selected_cat:
        st.session_state.quiz_state['active'] = False
        st.session_state.quiz_state['category'] = selected_cat

    # 4. 開始/重置按鈕
    if not st.session_state.quiz_state['active']:
        if st.button("開始測驗"):
            st.session_state.quiz_state['active'] = True
            st.session_state.quiz_state['score'] = 0
            st.session_state.quiz_state['total'] = 0
            st.session_state.quiz_state['show_answer'] = False
            # 抽取第一題
            pool = df[df['category'] == selected_cat]
            if not pool.empty:
                st.session_state.quiz_state['current_q'] = pool.sample(1).iloc[0].to_dict()
                st.rerun()
            else:
                st.error("此分類無題目！")

    # 5. 測驗進行中介面
    if st.session_state.quiz_state['active'] and st.session_state.quiz_state['current_q']:
        q = st.session_state.quiz_state['current_q']
        
        # 分數板
        st.markdown(f"### Score: {st.session_state.quiz_state['score']} / {st.session_state.quiz_state['total']}")
        st.progress(st.session_state.quiz_state['score'] / max(st.session_state.quiz_state['total'], 1))
        
        st.write("---")
        st.markdown("### 請問這個定義對應哪個單字？")
        st.markdown(f"<div class='responsive-definition' padding:20px; border-radius:20px;'>{q['definition']}</div>", unsafe_allow_html=True)
        st.markdown(f"**提示 (字根):** {q['roots']} ({q['meaning']})")

        # 顯示答案按鈕
        if not st.session_state.quiz_state['show_answer']:
            if st.button("看答案"):
                st.session_state.quiz_state['show_answer'] = True
                st.rerun()
        
        # 揭曉答案與評分
        else:
            st.write("---")
            st.markdown(f"<div class='responsive-word'>{q['word']}</div>", unsafe_allow_html=True)
            st.code(f"{q['breakdown']}")
            
            # 播放聲音
            speak(q['word'], key_suffix="quiz")

            c1, c2 = st.columns(2)
            with c1:
                if st.button("答對了", type="primary", use_container_width=True):
                    st.session_state.quiz_state['score'] += 1
                    st.session_state.quiz_state['total'] += 1
                    st.session_state.quiz_state['show_answer'] = False
                    # 下一題
                    pool = df[df['category'] == selected_cat]
                    st.session_state.quiz_state['current_q'] = pool.sample(1).iloc[0].to_dict()
                    st.rerun()
            with c2:
                if st.button("答錯了", use_container_width=True):
                    st.session_state.quiz_state['total'] += 1
                    st.session_state.quiz_state['show_answer'] = False
                    # 下一題
                    pool = df[df['category'] == selected_cat]
                    st.session_state.quiz_state['current_q'] = pool.sample(1).iloc[0].to_dict()
                    st.rerun()

# ==========================================
# 4. 主程式 (Main)
# ==========================================

def main():
    inject_custom_css()
    
    # 載入資料
    with st.spinner("正在讀取 Etymon 資料庫..."):
        df = load_db()
    
    if df.empty:
        st.error("無法讀取資料，請檢查 Google Sheet 連結或網路設定。")
        return

    # 側邊欄導航
    st.sidebar.title("Etymon")
    page = st.sidebar.radio("導航", ["首頁", "學習與搜尋", "測驗模式"])
    
    st.sidebar.markdown("---")
    st.sidebar.caption("v2.1 Refactored | by Etymon Dev")

    if page == "首頁":
        page_home(df)
    elif page == "學習與搜尋":
        page_learn_search(df)
    elif page == "測驗模式":
        page_quiz(df)

if __name__ == "__main__":
    main()
