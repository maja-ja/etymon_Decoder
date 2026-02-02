import streamlit as st
import pandas as pd
import base64
import time
import random
from io import BytesIO
from gtts import gTTS
from st_gsheets_connection import GSheetsConnection

# ==========================================
# 1. Core Config & Visuals (CSS)
# ==========================================
st.set_page_config(page_title="Etymon Decoder v2.5", page_icon="🧩", layout="wide")

def inject_custom_css():
    st.markdown("""
        <style>
            /* Hero Word Styling */
            .hero-word {
                font-size: 3.5rem !important;
                font-weight: 800;
                color: #1E88E5;
                margin-bottom: 0px;
                line-height: 1;
            }
            /* Phonetic Styling */
            .hero-phonetic {
                font-size: 1.2rem;
                color: #666;
                font-family: 'serif';
                margin-bottom: 20px;
            }
            /* Vibe Box Styling */
            .vibe-box {
                background-color: #f0f7ff;
                border-left: 5px solid #1E88E5;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
            }
            /* Operator Styling */
            .operator {
                color: #ff9800;
                font-weight: bold;
                padding: 0 5px;
            }
            .breakdown-container {
                font-family: monospace;
                font-size: 1.1rem;
                background: #f9f9f9;
                padding: 10px;
                border-radius: 5px;
            }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. Helper Functions (Audio & Data)
# ==========================================

def speak(text, key_suffix=""):
    """Text to Speech with hidden audio player"""
    try:
        if not text: return
        tts = gTTS(text=text, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        audio_base64 = base64.b64encode(fp.getvalue()).decode()
        unique_id = f"audio_{int(time.time())}_{key_suffix}"
        # Note: Autoplay policies in modern browsers might block this without user interaction
        st.components.v1.html(
            f'<audio id="{unique_id}" autoplay="true" style="display:none;"><source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3"></audio><script>document.getElementById("{unique_id}").play();</script>', 
            height=0
        )
    except Exception as e: 
        st.error(f"Audio Error: {e}")

@st.cache_data(ttl=600)
def load_db():
    """Load data from Google Sheets (Read-Only Public Link)"""
    COL_NAMES = [
        'category', 'roots', 'meaning', 'word', 'breakdown', 
        'definition', 'phonetic', 'example', 'translation', 'native_vibe',
        'synonym_nuance', 'visual_prompt', 'social_status', 'emotional_tone', 'street_usage',
        'collocation', 'etymon_story', 'usage_warning', 'memory_hook', 'audio_tag'
    ]
    SHEET_ID = '1W1ADPyf5gtGdpIEwkxBEsaJ0bksYldf4AugoXnq6Zvg'
    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&range=A:T'
    
    try:
        df = pd.read_csv(url)
        # Ensure alignment of 20 columns
        for i, col in enumerate(COL_NAMES):
            if i >= len(df.columns): df[col] = ""
        df.columns = COL_NAMES
        return df.dropna(subset=['word']).fillna("").reset_index(drop=True)
    except Exception as e:
        st.error(f"Database Connection Failed: {e}")
        return pd.DataFrame(columns=COL_NAMES)

def record_to_feedback(action, detail):
    """Write user actions to Feedback Sheet (Requires Secrets)"""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Target Sheet URL for Feedback
        FEEDBACK_URL = "https://docs.google.com/spreadsheets/d/1NNfKPadacJ6SDDLw9c23fmjq-26wGEeinTbWcg7-gFg/edit#gid=0"
        
        # Read existing to append (Note: In production, consider append-only API logic to avoid reading large datasets)
        existing_data = conn.read(spreadsheet=FEEDBACK_URL, worksheet="feedback")
        
        new_row = pd.DataFrame([{
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "detail": detail
        }])
        
        updated_df = pd.concat([existing_data, new_row], ignore_index=True)
        conn.update(spreadsheet=FEEDBACK_URL, worksheet="feedback", data=updated_df)
        return True # Return success status
    except Exception as e:
        print(f"Feedback Error: {e}")
        return False

# ==========================================
# 3. Component: Encyclopedia Card
# ==========================================

def show_encyclopedia_card(row):
    """Displays the main word card"""
    # --- Top: Word Hero ---
    st.markdown(f"<div class='hero-word'>{row['word']}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='hero-phonetic'>/{row['phonetic']}/</div>", unsafe_allow_html=True)
    
    col_a, col_b = st.columns([1, 4])
    with col_a:
        if st.button("🔊 朗讀", key=f"spk_{row['word']}", use_container_width=True):
            speak(row['word'], row['word'])
    with col_b:
        styled_breakdown = str(row['breakdown']).replace("+", "<span class='operator'>+</span>")
        st.markdown(f"<div class='breakdown-container'>{styled_breakdown}</div>", unsafe_allow_html=True)

    # --- Middle: Definition & Roots ---
    c1, c2 = st.columns(2)
    with c1:
        st.info(f"**🎯 定義：**\n{row['definition']}")
        st.write(f"**📝 例句：**\n{row['example']}")
        st.caption(f"（{row['translation']}）")
    with c2:
        st.success(f"**💡 字根：** {row['roots']}\n\n**意義：** {row['meaning']}")
        st.markdown(f"**🪝 記憶鉤子：**\n{row['memory_hook']}")

    # --- Feature: Native Vibe Surprise ---
    if row['native_vibe']:
        unlocked_key = f"unlocked_{row['word']}"
        if not st.session_state.get(unlocked_key, False):
            if st.button("🎁 拆開語感驚喜包 (Unlock Vibe)", use_container_width=True, type="secondary"):
                st.session_state[unlocked_key] = True
                st.balloons()
                st.rerun()
        else:
            st.markdown(f"""
                <div class='vibe-box'>
                    <h4 style='color:#1E88E5; margin-top:0;'>🌊 母語人士語感 (Native Vibe)</h4>
                    <p style='font-style: italic; font-size: 1.1rem;'>{row['native_vibe']}</p>
                </div>
            """, unsafe_allow_html=True)

    # --- Bottom: Deep Dive Tabs ---
    with st.expander("📚 查看深度百科 (文化、社會、街頭實戰)"):
        t1, t2, t3 = st.tabs(["🏛️ 字源文化", "👔 社會地位", "😎 街頭實戰"])
        with t1:
            st.write(f"**📜 字源故事：** {row['etymon_story']}")
            st.write(f"**⚖️ 同義詞辨析：** {row['synonym_nuance']}")
        with t2:
            st.write(f"**🎨 視覺提示：** {row['visual_prompt']}")
            st.write(f"**👔 社會感：** {row['social_status']} | **🌡️ 情緒值：** {row['emotional_tone']}")
        with t3:
            st.write(f"**🏙️ 街頭用法：** {row['street_usage']}")
            st.write(f"**🔗 常用搭配：** {row['collocation']}")
            if row['usage_warning']:
                st.error(f"⚠️ 使用警告：{row['usage_warning']}")

# ==========================================
# 4. Component: Monetization / Lead Gen
# ==========================================
def page_monetization_test():
    st.write("---")
    st.subheader("🚀 提升你的語感戰鬥力")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
            <div style='background-color: #f9f9f9; padding: 20px; border-radius: 10px; border: 1px dashed #1E88E5;'>
                <h4>🎁 領取免費資源</h4>
                <p>輸入信箱，獲取 <b>「100個母語者高頻字根思維導圖 (PDF)」</b></p>
            </div>
        """, unsafe_allow_html=True)
        email = st.text_input("Email Address", placeholder="example@email.com", key="input_email")
        
        if st.button("立即獲取地圖"):
            if "@" in email and "." in email:
                # Corrected function name
                success = record_to_feedback("EMAIL_LEAD", email)
                if success:
                    st.success("🎉 資料已送出！地圖將在系統上線後第一時間寄給你。")
                    st.balloons()
                else:
                    st.error("連線錯誤，請稍後再試。")
            else:
                st.warning("請輸入有效的信箱。")
        
    with col2:
        st.markdown("""
            <div style='background-color: #fff4e6; padding: 20px; border-radius: 10px; border: 1px solid #ff9800;'>
                <h4>💎 Etymon Decoder Pro</h4>
                <ul style='font-size: 0.9rem;'>
                    <li>AI 智能例句生成 (根據職業定制)</li>
                    <li>無限次語感驚喜包解鎖</li>
                    <li>離線複習模式與 Anki 匯出</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("查看訂閱方案 (每月 $150)", type="primary", use_container_width=True):
            record_to_feedback("PAY_INTENT", "Clicked Pro Plan button")
            st.session_state.show_payment_intent = True

    if st.session_state.get('show_payment_intent', False):
        st.info("💡 **感謝你的支持！** 我們正全力開發 Pro 功能。這是一個付費意願測試，你的點擊已紀錄，這將幫助我們加快開發速度！")
        if st.button("關閉", key="close_intent"):
            st.session_state.show_payment_intent = False
            st.rerun()

# ==========================================
# 5. Page Logic
# ==========================================
def page_home(df):
    st.markdown("<h1 style='text-align: center;'>Etymon Decoder</h1>", unsafe_allow_html=True)
    st.write("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("📚 總單字量", len(df))
    c2.metric("🏷️ 分類主題", df['category'].nunique())
    c3.metric("🧩 獨特字根", df['roots'].nunique())
    st.write("---")
    st.info("👈 請從左側選單進入「學習與搜尋」開啟您的語感之旅。")
    
    # Inject Monetization Test on Home Page
    page_monetization_test()

def page_learn_search(df):
    st.title("📖 學習與搜尋")
    tab_card, tab_list = st.tabs(["🎲 隨機探索", "🔍 資料庫列表"])
    
    with tab_card:
        # Filter
        cats = ["全部"] + sorted(df['category'].unique().tolist())
        sel_cat = st.selectbox("選擇學習分類", cats)
        f_df = df if sel_cat == "全部" else df[df['category'] == sel_cat]

        # Logic
        if st.button("下一個單字 (Next Word) ➔", use_container_width=True, type="primary"):
            st.session_state.curr_w = f_df.sample(1).iloc[0].to_dict()
            st.rerun()

        if 'curr_w' not in st.session_state and not f_df.empty:
            st.session_state.curr_w = f_df.sample(1).iloc[0].to_dict()

        if 'curr_w' in st.session_state:
            show_encyclopedia_card(st.session_state.curr_w)

    with tab_list:
        search = st.text_input("🔍 搜尋單字、字根或中文定義...", placeholder="例如: 'bio' 或 '生命'...")
        if search:
            mask = df.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)
            display_df = df[mask]
        else:
            display_df = df.head(50)
            
        st.write(f"顯示 {len(display_df)} 筆結果")
        st.dataframe(display_df[['word', 'definition', 'roots', 'category', 'native_vibe']], use_container_width=True)

def page_quiz(df):
    st.title("🧠 字根記憶挑戰")
    cat = st.selectbox("選擇測驗範圍", df['category'].unique())
    pool = df[df['category'] == cat]
    
    if st.button("🎲 抽一題", use_container_width=True):
        st.session_state.q = pool.sample(1).iloc[0].to_dict()
        st.session_state.show_ans = False
        st.rerun()

    if 'q' in st.session_state:
        st.markdown(f"### ❓ 請問這對應哪個單字？")
        st.info(st.session_state.q['definition'])
        st.write(f"**提示 (字根):** {st.session_state.q['roots']} ({st.session_state.q['meaning']})")
        
        if st.button("揭曉答案"):
            st.session_state.show_ans = True
            st.rerun()
        
        if st.session_state.get('show_ans', False):
            st.success(f"💡 答案是：**{st.session_state.q['word']}**")
            speak(st.session_state.q['word'], "quiz")
            st.write(f"結構拆解：`{st.session_state.q['breakdown']}`")

# ==========================================
# 6. Main Execution
# ==========================================
def main():
    inject_custom_css()
    df = load_db()
    
    if df.empty:
        st.warning("無法載入資料庫，請檢查 Google Sheets 權限或網路連線。")
        return

    st.sidebar.title("Etymon Decoder")
    page = st.sidebar.radio("功能選單", ["首頁", "學習與搜尋", "測驗模式"])
    st.sidebar.markdown("---")
    st.sidebar.caption("v2.5 百科全書版 | 2026 Refactored")

    if page == "首頁":
        page_home(df)
    elif page == "學習與搜尋":
        page_learn_search(df)
        st.sidebar.markdown("---")
        if st.sidebar.button("🔓 解鎖 AI 深度解說 (Pro)"):
            st.toast("Pro 功能開發中！感謝你的關注。")
    elif page == "測驗模式":
        page_quiz(df)

if __name__ == "__main__":
    main()
