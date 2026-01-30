import streamlit as st
import pandas as pd
import base64
import time
import json
import random
from io import BytesIO
from gtts import gTTS
import streamlit.components.v1 as components

# ==========================================
# 1. 核心配置與 CSS (完全回復 v2.5 視覺)
# ==========================================
st.set_page_config(page_title="Etymon Decoder v2.5 Hybrid", page_icon="🧩", layout="wide")

def inject_custom_css():
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=Noto+Sans+TC:wght@500;700&display=swap');

            .breakdown-container {
                font-family: 'Inter', 'Noto Sans TC', sans-serif; 
                font-size: 1.8rem !important; 
                font-weight: 700;
                background: linear-gradient(135deg, #1E88E5 0%, #1565C0 100%);
                color: #FFFFFF;
                padding: 12px 30px;
                border-radius: 15px;
                display: inline-block;
                margin: 20px 0;
                box-shadow: 0 4px 15px rgba(30, 136, 229, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            .breakdown-container span.operator { color: #BBDEFB; margin: 0 8px; }
            .hero-word { font-size: 4.5rem; font-weight: 900; color: #1E88E5; line-height: 1.2; }
            .hero-phonetic { font-size: 1.8rem; color: #666; margin-bottom: 10px; }
            .vibe-box {
                background: #f0f7ff;
                border-left: 5px solid #1E88E5;
                padding: 25px;
                border-radius: 15px;
                margin: 20px 0;
            }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 核心功能：雲端讀取與語音
# ==========================================
def speak(text, key_suffix=""):
    try:
        tts = gTTS(text=text, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        audio_base64 = base64.b64encode(fp.getvalue()).decode()
        unique_id = f"audio_{int(time.time())}_{key_suffix}"
        st.components.v1.html(f'<audio id="{unique_id}" autoplay="true" style="display:none;"><source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3"></audio><script>document.getElementById("{unique_id}").play();</script>', height=0)
    except: pass

@st.cache_data(ttl=30)
def load_db():
    COL_NAMES = [
        'category', 'roots', 'meaning', 'word', 'breakdown', 
        'definition', 'phonetic', 'example', 'translation', 'native_vibe',
        'synonym_nuance', 'visual_prompt', 'social_status', 'emotional_tone', 'street_usage',
        'collocation', 'etymon_story', 'usage_warning', 'memory_hook', 'audio_tag'
    ]
    SHEET_ID = "1W1ADPyf5gtGdpIEwkxBEsaJ0bksYldf4AugoXnq6Zvg"
    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&range=A:T'
    try:
        df = pd.read_csv(url)
        for i, col in enumerate(COL_NAMES):
            if i >= len(df.columns): df[col] = ""
        df.columns = COL_NAMES
        return df.dropna(subset=['word']).fillna("").reset_index(drop=True)
    except: return pd.DataFrame(columns=COL_NAMES)

# ==========================================
# 3. 百科全書卡片 (完全恢復 20 欄位顯示)
# ==========================================
def show_encyclopedia_card(row):
    st.markdown(f"<div class='hero-word'>{row['word']}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='hero-phonetic'>/{row['phonetic']}/</div>", unsafe_allow_html=True)
    
    col_a, col_b = st.columns([1, 4])
    with col_a:
        if st.button("🔊 朗讀", key=f"spk_{row['word']}", use_container_width=True):
            speak(row['word'], row['word'])
    with col_b:
        styled_breakdown = str(row['breakdown']).replace("+", "<span class='operator'>+</span>")
        st.markdown(f"<div class='breakdown-container'>{styled_breakdown}</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.info(f"**🎯 定義：**\n{row['definition']}")
        st.write(f"**📝 例句：**\n{row['example']}")
        st.caption(f"（{row['translation']}）")
    with c2:
        st.success(f"**💡 字根：** {row['roots']}\n\n**意義：** {row['meaning']}")
        st.markdown(f"**🪝 記憶鉤子：**\n{row['memory_hook']}")

    if row['native_vibe']:
        u_key = f"unlocked_{row['word']}"
        if not st.session_state.get(u_key, False):
            if st.button("🎁 拆開語感驚喜包", key=f"gift_{row['word']}", use_container_width=True):
                st.session_state[u_key] = True
                st.balloons()
                st.rerun()
        else:
            st.markdown(f"<div class='vibe-box'><b>🌊 母語語感：</b><br>{row['native_vibe']}</div>", unsafe_allow_html=True)

    with st.expander("📚 查看深度百科 (文化/地位/實戰)"):
        t1, t2, t3 = st.tabs(["🏛️ 字源文化", "👔 社會地位", "😎 街頭實戰"])
        with t1:
            st.write(f"**📜 字源故事：** {row['etymon_story']}")
            st.write(f"**⚖️ 同義詞辨析：** {row['synonym_nuance']}")
        with t2:
            st.write(f"**🎨 視覺提示：** {row['visual_prompt']}")
            st.write(f"**👔 社會感：** {row['social_status']} | **🌡️ 情緒值：** {row['emotional_tone']}")
        with t3:
            st.write(f"**🏙️ 街頭用法：** {row['street_usage']} | **🔗 常用搭配：** {row['collocation']}")
            if row['usage_warning']: st.error(f"⚠️ 警告：{row['usage_warning']}")

# ==========================================
# 4. 修正版實驗室 (解決文字遮擋)
# ==========================================
def render_react_lab():
    lab_data = [
        {"word": "neuromorphic", "p": "neuro", "r": "morphic", "definition": "類神經型態的", "vibe": "模擬大腦神經元結構。", "phonetic": "ˌnjʊəroʊˈmɔːrfɪk"},
        {"word": "hyperdimensional", "p": "hyper", "r": "dimensional", "definition": "高維空間的", "vibe": "LLM 運算的數學核心。", "phonetic": "ˌhaɪpərdɪˈmɛnʃənl"},
        {"word": "autopoietic", "p": "auto", "r": "poietic", "definition": "自我生成的", "vibe": "系統具備自我維護的生命力。", "phonetic": "ˌɔːtoʊpɔɪˈɛtɪk"}
    ]
    payload = {
        "prefixes": [{"id": p, "label": f"{p}-"} for p in sorted(set(d['p'] for d in lab_data))],
        "roots": [{"id": r, "label": f"-{r}"} for r in sorted(set(d['r'] for d in lab_data))],
        "dictionary": lab_data
    }
    
    html_code = """
    <!DOCTYPE html><html><head>
        <script src="https://unpkg.com/react@18/umd/react.development.js"></script>
        <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
        <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
        <script src="https://cdn.tailwindcss.com"></script>
        <style> .no-scrollbar::-webkit-scrollbar { display: none; } .mask { background: linear-gradient(180deg, white 0%, transparent 30%, transparent 70%, white 100%); } </style>
    </head>
    <body class="bg-transparent"><div id="root"></div>
    <script type="text/babel">
        const { useState, useRef, useEffect } = React;
        const DATA = REPLACE_ME;
        const Wheel = ({ items, onSelect, label }) => {
            const ref = useRef(null);
            useEffect(() => { if(ref.current) ref.current.scrollTop = 0; }, []);
            return (
                <div className="flex flex-col items-center">
                    <div className="text-[10px] font-bold text-gray-400 mb-1 uppercase tracking-widest">{label}</div>
                    <div className="relative w-32 h-36 bg-white rounded-2xl shadow-inner border border-gray-200 overflow-hidden">
                        <div className="absolute top-[46px] w-full h-[44px] bg-blue-50 border-y border-blue-100 z-0"></div>
                        <div ref={ref} onScroll={() => {
                            const idx = Math.round(ref.current.scrollTop / 44);
                            if(items[idx]) onSelect(items[idx].id);
                        }} className="h-full overflow-y-scroll snap-y snap-mandatory no-scrollbar py-[46px] relative z-10">
                            {items.map(i => <div key={i.id} className="h-[44px] flex items-center justify-center snap-center font-bold text-gray-600 text-lg">{i.label}</div>)}
                        </div>
                        <div className="absolute inset-0 mask pointer-events-none z-20"></div>
                    </div>
                </div>
            );
        };
        const App = () => {
            const [p, setP] = useState(DATA.prefixes[0].id);
            const [r, setR] = useState(DATA.roots[0].id);
            const m = DATA.dictionary.find(d => d.p === p && d.r === r);
            return (
                <div className="flex flex-col items-center p-4">
                    <div className="flex items-center gap-4 mb-10">
                        <Wheel items={DATA.prefixes} onSelect={setP} label="Prefix" />
                        <div className="text-3xl text-gray-300 mt-6">+</div>
                        <Wheel items={DATA.roots} onSelect={setR} label="Root" />
                    </div>
                    {m ? (
                        <div className="w-full bg-white p-8 rounded-[2.5rem] shadow-2xl border border-blue-50 transition-all">
                            <h1 className="text-5xl font-black text-blue-600 mb-2 leading-tight">{m.word}</h1>
                            <p className="text-gray-400 font-mono mb-6 text-xl">/{m.phonetic}/</p>
                            <div className="bg-blue-50 p-5 rounded-2xl text-blue-900 font-bold text-lg mb-4">{m.definition}</div>
                            <p className="italic text-gray-500 font-medium text-lg">"{m.vibe}"</p>
                        </div>
                    ) : (
                        <div className="w-full h-32 flex flex-col items-center justify-center border-2 border-dashed border-gray-100 rounded-[2.5rem] bg-gray-50/50">
                            <span className="text-gray-300 italic text-xl">🧬 Spinning Decoder...</span>
                        </div>
                    )}
                </div>
            );
        };
        ReactDOM.createRoot(document.getElementById('root')).render(<App />);
    </script></body></html>
    """.replace("REPLACE_ME", json.dumps(payload))
    components.html(html_code, height=600)
# ==========================================
# 5. 主程式架構 (世代導航版)
# ==========================================
def main():
    inject_custom_css()
    df = load_db()
    
    # --- 1. 定義新 App 的連結 ---
    # 請將下方網址替換成你部署好的「新世代醫學宇宙」網址
    NEW_ERA_APP_URL = "https://www.google.com"
    
    # --- 2. 側邊欄頂部：世代切換區 ---
    st.sidebar.title("Era Gateway")
    
    # 使用 columns 讓按鈕並排或呈現對比
    c1, c2 = st.sidebar.columns(2)
    with c1:
        st.button("舊世代", disabled=True, use_container_width=True, help="目前所在位置")
    with c2:
        # 這裡是通往新 App 的關鍵
        if st.button("新世代", help="前往全學段解碼宇宙"):
            # 透過 HTML 自動跳轉
            js = f"window.open('{NEW_ERA_APP_URL}', '_self')"
            st.components.v1.html(f"<script>{js}</script>", height=0)
            st.markdown(f"[手動進入K宇宙]({NEW_ERA_APP_URL})")

    st.sidebar.markdown("---")

    # --- 3. 原本的功能選單 (對應截圖中的位置) ---
    st.sidebar.title("Etymon Decoder") # 截圖中的標題
    page = st.sidebar.radio(
        "功能選單", 
        ["首頁", "學習與搜尋", "測驗模式", "Mix Lab 實驗室"],
        index=0
    )
    
    st.sidebar.markdown("---")
    # ... 後續原本的 if page == "..." 邏輯 ...
    if page == "首頁":
        st.markdown("<h1 style='text-align: center;'>Etymon Decoder</h1>", unsafe_allow_html=True)
        st.write("---")
        # 顯示官方移交公告（如果你想的話）
        st.warning("本計劃已移交繼承者。新計畫請點擊左側「新世代」。")
        
        c1, c2, c3 = st.columns(3)
        if not df.empty:
            c1.metric("雲端總量", len(df))
            c2.metric("分類主題", df['category'].nunique())
            c3.metric("字根庫", df['roots'].nunique())
        st.info("請從左側選單選擇功能。")

    elif page == "學習與搜尋":
        st.title("學習與搜尋")
        tab_card, tab_list = st.tabs(["🎲 隨機探索", "🔍 資料庫列表"])
        with tab_card:
            cats = ["全部"] + sorted(df['category'].unique().tolist())
            sel_cat = st.selectbox("分類篩選", cats)
            f_df = df if sel_cat == "全部" else df[df['category'] == sel_cat]
            if st.button("下一個單字 ➔", type="primary"):
                st.session_state.curr_w = f_df.sample(1).iloc[0].to_dict()
                st.rerun()
            if 'curr_w' in st.session_state:
                show_encyclopedia_card(st.session_state.curr_w)
        with tab_list:
            search = st.text_input("🔍 搜尋關鍵字...")
            if search:
                mask = df.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)
                st.dataframe(df[mask][['word', 'definition', 'roots', 'category']], use_container_width=True)
            else:
                st.dataframe(df.head(50)[['word', 'definition', 'roots', 'category']], use_container_width=True)

    elif page == "測驗模式":
        st.title("字根記憶挑戰")
        if not df.empty:
            cat = st.selectbox("測驗範圍", df['category'].unique())
            pool = df[df['category'] == cat]
            if st.button("🎲 抽題", use_container_width=True):
                st.session_state.q = pool.sample(1).iloc[0].to_dict()
                st.session_state.show_ans = False
            if 'q' in st.session_state:
                st.markdown("### ❓ 請問這是哪個單字？")
                st.info(st.session_state.q['definition'])
                st.write(f"提示 (字根): {st.session_state.q['roots']}")
                if st.button("揭曉答案"): st.session_state.show_ans = True
                if st.session_state.get('show_ans'):
                    st.success(f"答案：**{st.session_state.q['word']}**")
                    speak(st.session_state.q['word'], "quiz")

    elif page == "Mix Lab 實驗室":
        st.title("Mix Lab 實驗室")
        render_react_lab()

if __name__ == "__main__":
    main()
