import streamlit as st
import pandas as pd
import base64
import time
import json
import re  # Used for precise JSON extraction and text cleaning
from io import BytesIO
from gtts import gTTS
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. Core Configuration & Visual Styling (CSS)
# ==========================================
st.set_page_config(page_title="Etymon Decoder v3.0", page_icon="🧩", layout="wide")

def inject_custom_css():
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=Noto+Sans+TC:wght@500;700&display=swap');
            
            /* 1. Breakdown Block (Gradient Border) */
            .breakdown-wrapper {
                background: linear-gradient(135deg, #1E88E5 0%, #1565C0 100%);
                padding: 25px 30px;
                border-radius: 15px;
                box-shadow: 0 4px 15px rgba(30, 136, 229, 0.3);
                margin: 20px 0;
                color: white !important;
            }
            
            /* 2. LaTeX Engine Fix: Remove black blocks, make text white */
            .breakdown-wrapper .katex {
                color: #FFFFFF !important;
                background: transparent !important;
                font-size: 1.15em;
            }
            .breakdown-wrapper .katex-display {
                background: transparent !important;
                margin: 1em 0;
            }

            /* 3. Force content text and lists to be white and wrap */
            .breakdown-wrapper p, .breakdown-wrapper li, .breakdown-wrapper span {
                color: white !important;
                font-weight: 700 !important;
                line-height: 1.7;
                white-space: pre-wrap !important;
            }

            /* 4. Vibe and Title Styling */
            .hero-word { font-size: 2.8rem; font-weight: 800; color: #1A237E; }
            @media (prefers-color-scheme: dark) { .hero-word { color: #90CAF9; } }
            
            .vibe-box { 
                background-color: #F0F7FF; padding: 20px; border-radius: 12px; 
                border-left: 6px solid #2196F3; color: #2C3E50 !important; margin: 15px 0;
            }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. Utility Functions
# ==========================================

def fix_content(text):
    """
    Global string cleaning (Fixes LaTeX and Newlines):
    1. Handles nulls and 'nan'.
    2. Processes newlines first, then LaTeX escapes to avoid conflict.
    3. Optimized for Markdown newline requirements.
    """
    if text is None or str(text).strip() in ["無", "nan", ""]:
        return ""
    
    # Ensure string type
    text = str(text)
    
    # --- Fix 1: Handle Newlines ---
    # AI sometimes outputs \\n, sometimes \n. 
    # Convert to Markdown's "two spaces + newline" for pretty lists.
    text = text.replace('\\n', '  \n').replace('\n', '  \n')
    
    # --- Fix 2: Handle LaTeX Backslashes ---
    # If data has \\frac, it's over-escaped. Restore to \frac for st.markdown.
    # Be careful not to break existing single backslashes.
    if '\\\\' in text:
        text = text.replace('\\\\', '\\')
    
    # --- Fix 3: Clean JSON Quote Residue ---
    # Remove excessive quotes AI might leave around strings
    text = text.strip('"').strip("'")
    
    return text

def speak(text, key_suffix=""):
    """
    Generates audio using gTTS and displays a native Streamlit audio player.
    This prevents browser autoplay blocking and ensures reliability.
    """
    if not text:
        return
    
    # 1. English Filter
    # Only keep Alphanumeric, spaces, hyphens, apostrophes
    english_only = re.sub(r"[^a-zA-Z0-9\s\-\']", " ", str(text))
    english_only = " ".join(english_only.split()).strip()
    
    if not english_only:
        return

    try:
        # 2. Generate the Audio
        tts = gTTS(text=english_only, lang='en')
        audio_buffer = BytesIO()
        tts.write_to_fp(audio_buffer)
        
        # 3. Display the native Streamlit audio player
        # Use a unique key to ensure player updates if text changes
        st.audio(audio_buffer, format="audio/mp3", start_time=0)
        
    except Exception as e:
        st.error(f"Speech Error: {e}")

def get_spreadsheet_url():
    """Safely get spreadsheet URL, compatible with two secrets formats."""
    try:
        return st.secrets["connections"]["gsheets"]["spreadsheet"]
    except:
        try:
            return st.secrets["gsheets"]["spreadsheet"]
        except:
            st.error("Cannot find spreadsheet config. Please check secrets.toml")
            return ""

@st.cache_data(ttl=3600) 
def load_db():
    # Define standard 20 columns
    COL_NAMES = [
        'category', 'roots', 'meaning', 'word', 'breakdown', 
        'definition', 'phonetic', 'example', 'translation', 'native_vibe',
        'synonym_nuance', 'visual_prompt', 'social_status', 'emotional_tone', 'street_usage',
        'collocation', 'etymon_story', 'usage_warning', 'memory_hook', 'audio_tag'
    ]
    
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        url = get_spreadsheet_url()
        
        # Read data (ttl=0 to bypass connection cache, rely on st.cache_data)
        df = conn.read(spreadsheet=url, ttl=0)
        
        # 1. Fill missing columns with "無"
        for col in COL_NAMES:
            if col not in df.columns:
                df[col] = "無"
        
        # 2. Data Cleaning: Remove rows where 'word' is empty, fill NaNs
        df = df.dropna(subset=['word'])
        df = df.fillna("無")
        
        # 3. Sort columns
        return df[COL_NAMES].reset_index(drop=True)
        
    except Exception as e:
        st.error(f"❌ Database Load Failed: {e}")
        return pd.DataFrame(columns=COL_NAMES)

# ==========================================
# 3. AI Decode Core (Unlock Version)
# ==========================================
def ai_decode_and_save(input_text, fixed_category):
    """
    Core decoding function: Prompts directly in code for stability.
    """
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("❌ GEMINI_API_KEY not found in Streamlit Secrets.")
        return None

    genai.configure(api_key=api_key)
    
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    SYSTEM_PROMPT = f"""
    Role: Polymath Decoder.
    Task: Analyze input and deconstruct into high-quality, structured JSON.
    
    [Domain Lock]: You are an expert in "{fixed_category}". Decode from this perspective.

    ## Field Mapping Strategy:
    1. category: Must be "{fixed_category}".
    2. word: Core concept name (Title).
    3. roots: Underlying logic / Core principle / Key Formula. Use LaTeX format wrapped in $.
    4. meaning: Core pain point solved or essential meaning.
    5. breakdown: Structural breakdown. Steps or components, listed with \\n.
    6. definition: ELI5 explanation.
    7. phonetic: Key era, inventor, or specific terminology. IPA or transliteration for foreign words.
    8. example: 2+ representative application scenarios.
    9. translation: Life Analogy. Start with "🍎 Life Analogy:".
    10. native_vibe: Expert Insight. Start with "🌊 Expert Vibe:".
    11. synonym_nuance: Comparison with similar concepts.
    12. visual_prompt: Visualization description.
    13. social_status: Importance rating in the field.
    14. emotional_tone: Psychological feeling of learning this.
    15. street_usage: Common misconceptions.
    16. collocation: Knowledge Graph. 3 related points.
    17. etymon_story: History or discovery moment.
    18. usage_warning: Boundary conditions or failure scenarios.
    19. memory_hook: Memory slogan.
    20. audio_tag: Related tags (start with #).

    ## Strict JSON Rules:
    1. Output PURE JSON only. No Markdown tags (like ```json).
    2. All Keys and String Values must be double-quoted ("). Use single quotes or Chinese quotes inside strings.
    3. LaTeX formulas use single backslash, but double escape in JSON (e.g., \\\\frac).
    4. Use \\\\n for newlines.
    """
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp', safety_settings=safety_settings)
        final_prompt = f"{SYSTEM_PROMPT}\n\nTarget:「{input_text}」"
        
        response = model.generate_content(final_prompt)
        
        if response and response.text:
            return response.text
        return None
    except Exception as e:
        st.error(f"Gemini API Error: {e}")
        return None

def show_encyclopedia_card(row):
    # 1. Variable Cleaning
    r_word = str(row.get('word', 'Untitled'))
    r_roots = fix_content(row.get('roots', "")).replace('$', '$$')
    r_phonetic = fix_content(row.get('phonetic', "")) 
    r_breakdown = fix_content(row.get('breakdown', ""))
    r_def = fix_content(row.get('definition', ""))
    r_roots = fix_content(row.get('roots', ""))
    r_meaning = str(row.get('meaning', ""))
    r_hook = fix_content(row.get('memory_hook', ""))
    r_vibe = fix_content(row.get('native_vibe', ""))
    r_trans = str(row.get('translation', ""))

    # 2. Hero Word
    st.markdown(f"<div class='hero-word'>{r_word}</div>", unsafe_allow_html=True)
    
    # 3. Sub-description
    if r_phonetic and r_phonetic != "無":
        st.markdown(f"""
            <div style='color: #E0E0E0; font-size: 0.95rem; margin-bottom: 20px; line-height: 1.6; opacity: 0.9;'>
            {r_phonetic}
            </div>
        """, unsafe_allow_html=True)

    # 4. Audio & Breakdown Area
    col_a, col_b = st.columns([1, 4])
    with col_a:
        # --- AUDIO PLAYER INTEGRATION ---
        # Instead of a button that reruns the script, we display the player directly.
        st.caption("🔊 Pronunciation")
        speak(r_word, key_suffix="card_main")
            
    with col_b:
        st.markdown(f"#### 🧬 Logic Breakdown\n{r_breakdown}")

    # 5. Dual Column Core Area
    st.write("---")
    c1, c2 = st.columns(2)
    r_ex = fix_content(row.get('example', ""))
    
    with c1:
        st.info("### 🎯 Definition & Explanation")
        st.markdown(r_def) 
        st.markdown(f"**📝 Application / Steps:** \n{r_ex}")
        if r_trans and r_trans != "無":
            st.caption(f"（{r_trans}）")
        
    with c2:
        st.success("### 💡 Core Principle")
        st.markdown(r_roots)
        st.write(f"**🔍 Essence:** {r_meaning}")
        st.markdown(f"**🪝 Memory Hook:** \n{r_hook}")

    # 6. Expert Vibe
    if r_vibe:
        st.markdown("""
            <div class='vibe-box'>
                <h4 style='margin-top:0; color:#1565C0;'>🌊 Expert Vibe</h4>
        """, unsafe_allow_html=True)
        st.markdown(r_vibe)
        st.markdown("</div>", unsafe_allow_html=True)

    # 7. Deep Dive Expander
    with st.expander("🔍 Deep Dive (Nuance, History, Warnings)"):
        sub_c1, sub_c2 = st.columns(2)
        with sub_c1:
            st.markdown(f"**⚖️ Comparison:** \n{fix_content(row.get('synonym_nuance', '無'))}")
            st.markdown(f"**🏛️ History:** \n{fix_content(row.get('etymon_story', '無'))}")
        with sub_c2:
            st.markdown(f"**⚠️ Warnings:** \n{fix_content(row.get('usage_warning', '無'))}")
            st.markdown(f"**🏙️ Graph:** \n{fix_content(row.get('collocation', '無'))}")

# ==========================================
# 4. Page Logic
# ==========================================

def page_ai_lab():
    st.title("🔬 Kadowsella Decoding Lab")
    
    FIXED_CATEGORIES = [
        "英語辭源", "語言邏輯", "物理科學", "生物醫學", "天文地質", "數學邏輯", 
        "歷史文明", "政治法律", "社會心理", "哲學宗教", "軍事戰略", "考古發現",
        "商業商戰", "金融投資", "程式開發", "人工智慧", "產品設計", "數位行銷",
        "藝術美學", "影視文學", "料理食觀", "運動健身", "流行文化", "雜類", "自定義"
    ]
    
    col_input, col_cat = st.columns([2, 1])
    with col_input:
        new_word = st.text_input("Enter Topic:", placeholder="e.g., 'Vertex Form'")
    with col_cat:
        selected_category = st.selectbox("Category", FIXED_CATEGORIES)
        
    if selected_category == "自定義":
        custom_cat = st.text_input("Custom Category Name:")
        final_category = custom_cat if custom_cat else "Uncategorized"
    else:
        final_category = selected_category

    force_refresh = st.checkbox("🔄 Force Refresh (Overwrite)")
    
    if st.button("Start Decoding", type="primary"):
        if not new_word:
            st.warning("Please enter a topic.")
            return

        conn = st.connection("gsheets", type=GSheetsConnection)
        url = get_spreadsheet_url()
        existing_data = conn.read(spreadsheet=url, ttl=0)
        
        is_exist = False
        if not existing_data.empty:
            match_mask = existing_data['word'].astype(str).str.lower() == new_word.lower()
            is_exist = match_mask.any()

        if is_exist and not force_refresh:
            st.warning(f"⚠️ '{new_word}' is already on the shelf.")
            show_encyclopedia_card(existing_data[match_mask].iloc[0].to_dict())
            return

        with st.spinner(f'Decoding via [{final_category}] perspective...'):
            raw_res = ai_decode_and_save(new_word, final_category)
            
            if raw_res is None:
                st.error("AI No Response.")
                return

            try:
                match = re.search(r'\{.*\}', raw_res, re.DOTALL)
                if not match:
                    st.error("Parse Failed: No JSON found.")
                    return
                
                json_str = match.group(0)

                try:
                    res_data = json.loads(json_str, strict=False)
                except json.JSONDecodeError:
                    fixed_json = json_str.replace('\n', '\\n').replace('\r', '\\r')
                    res_data = json.loads(fixed_json, strict=False)

                if is_exist and force_refresh:
                    existing_data = existing_data[~match_mask]
                
                new_row = pd.DataFrame([res_data])
                updated_df = pd.concat([existing_data, new_row], ignore_index=True)
                
                conn.update(spreadsheet=url, data=updated_df)
                st.success(f"🎉 '{new_word}' decoded and saved!")
                st.balloons()
                show_encyclopedia_card(res_data)

            except Exception as e:
                st.error(f"⚠️ Processing Failed: {e}")
                with st.expander("Raw Error Data"):
                    st.code(raw_res)

def page_home(df):
    st.markdown("<h1 style='text-align: center;'>Etymon Decoder</h1>", unsafe_allow_html=True)
    st.write("---")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("📚 Total Words", len(df))
    c2.metric("🏷️ Topics", df['category'].nunique() if not df.empty else 0)
    c3.metric("🧩 Roots", df['roots'].nunique() if not df.empty else 0)
    
    st.write("---")

    st.subheader("💡 Today's Picks")
    
    if not df.empty:
        sample_count = min(3, len(df))
        sample = df.sample(sample_count)
        
        cols = st.columns(3)
        for i, (index, row) in enumerate(sample.iterrows()):
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"### {row['word']}")
                    st.caption(f"🏷️ {row['category']}")
                    
                    cleaned_def = fix_content(row['definition'])
                    cleaned_roots = fix_content(row['roots'])
                    
                    st.markdown(f"**Def:** {cleaned_def}")
                    st.markdown(f"**Core:** {cleaned_roots}")

                    # --- AUDIO FIX ---
                    # Use unique key suffix to avoid ID collisions
                    speak(row['word'], key_suffix=f"home_{i}")

    st.write("---")
    st.info("👈 Click 'Study & Search' in the sidebar to view full database.")

def page_learn_search(df):
    st.title("📖 Study & Search")
    if df.empty:
        st.warning("Bookshelf is empty.")
        return

    tab_card, tab_list = st.tabs(["🎲 Random Explore", "🔍 Database List"])
    
    with tab_card:
        cats = ["All"] + sorted(df['category'].unique().tolist())
        sel_cat = st.selectbox("Select Category", cats)
        f_df = df if sel_cat == "All" else df[df['category'] == sel_cat]

        # --- SESSION STATE LOCK LOGIC ---
        # 1. Initialize State
        if 'curr_w' not in st.session_state:
            st.session_state.curr_w = None

        # 2. Button only updates State (Change Question)
        if st.button("Next Word (Random) ➔", use_container_width=True, type="primary"):
            if not f_df.empty:
                st.session_state.curr_w = f_df.sample(1).iloc[0].to_dict()
                st.rerun() # Refresh to show new card
            else:
                st.warning("No data in this category.")

        # 3. Initial Load (if empty)
        if st.session_state.curr_w is None and not f_df.empty:
            st.session_state.curr_w = f_df.sample(1).iloc[0].to_dict()

        # 4. Show Card (Audio is inside the card function)
        if st.session_state.curr_w:
            show_encyclopedia_card(st.session_state.curr_w)

    with tab_list:
        search = st.text_input("🔍 Search shelf...")
        if search:
            mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
            display_df = df[mask]
        else:
            display_df = df.head(50)
        st.dataframe(display_df[['word', 'definition', 'roots', 'category', 'native_vibe']], use_container_width=True)

def page_quiz(df):
    st.title("🧠 Memory Challenge")
    if df.empty: return
    
    cat = st.selectbox("Select Quiz Range", df['category'].unique())
    pool = df[df['category'] == cat]
    
    # Initialize Quiz State
    if 'q' not in st.session_state:
        st.session_state.q = None
    if 'show_ans' not in st.session_state:
        st.session_state.show_ans = False

    if st.button("🎲 Draw Question", use_container_width=True):
        st.session_state.q = pool.sample(1).iloc[0].to_dict()
        st.session_state.show_ans = False
        st.rerun()

    if st.session_state.q:
        st.markdown(f"### ❓ Which word matches this definition?")
        st.info(st.session_state.q['definition'])
        st.write(f"**Hint (Roots):** {st.session_state.q['roots']} ({st.session_state.q['meaning']})")
        
        if st.button("Reveal Answer"):
            st.session_state.show_ans = True
            st.rerun()
        
        if st.session_state.show_ans:
            st.success(f"💡 Answer: **{st.session_state.q['word']}**")
            # Native Audio Player
            speak(st.session_state.q['word'], "quiz")
            st.write(f"Breakdown: `{st.session_state.q['breakdown']}`")

# ==========================================
# 5. Main Entry
# ==========================================
def main():
    inject_custom_css()
    
    st.sidebar.title("Kadowsella")
    
    # --- Sponsor Block ---
    st.sidebar.markdown("""
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 12px; border: 1px solid #e9ecef; margin-bottom: 25px;">
            <p style="text-align: center; margin-bottom: 12px; font-weight: bold; color: #444;">💖 Support Dev</p>
            <a href="[https://www.buymeacoffee.com/kadowsella](https://www.buymeacoffee.com/kadowsella)" target="_blank" style="text-decoration: none;">
                <div style="background-color: #FFDD00; color: #000; padding: 8px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 8px; font-size: 0.9rem;">
                    ☕ Buy Me a Coffee
                </div>
            </a>
            <a href="[https://p.ecpay.com.tw/kadowsella20](https://p.ecpay.com.tw/kadowsella20)" target="_blank" style="text-decoration: none;">
                <div style="background: linear-gradient(90deg, #28C76F 0%, #81FBB8 100%); color: white; padding: 8px; border-radius: 8px; text-align: center; font-weight: bold; font-size: 0.9rem;">
                    Donate!
                </div>
            </a>
        </div>
    """, unsafe_allow_html=True)
    
    # --- Admin Login ---
    is_admin = False
    with st.sidebar.expander("🔐 Admin Login", expanded=False):
        input_pass = st.text_input("Password", type="password")
        if input_pass == st.secrets.get("ADMIN_PASSWORD", "0000"):
            is_admin = True
            st.success("🔓 God Mode")

    # --- Menu Logic ---
    if is_admin:
        menu_options = ["Home", "Study & Search", "Quiz Mode", "🔬 Decoding Lab"]
        if st.sidebar.button("🔄 Sync Cloud", help="Clear App Cache"):
            st.cache_data.clear()
            st.rerun()
    else:
        menu_options = ["Home", "Study & Search", "Quiz Mode"]
    
    page = st.sidebar.radio("Menu", menu_options)
    st.sidebar.markdown("---")
    
    df = load_db()
    
    if page == "Home":
        page_home(df)
    elif page == "Study & Search":
        page_learn_search(df)
    elif page == "Quiz Mode":
        page_quiz(df)
    elif page == "🔬 Decoding Lab":
        if is_admin:
            page_ai_lab()
        else:
            st.error("⛔ Please login")

    status = "🔴 Admin" if is_admin else "🟢 Guest"
    st.sidebar.caption(f"v3.0 Ultimate | {status}")

if __name__ == "__main__":
    main()
