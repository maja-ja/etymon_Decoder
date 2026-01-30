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
# 1. 核心配置與 CSS (保留 v2.5 所有視覺)
# ==========================================
st.set_page_config(page_title="Etymon Decoder Hybrid", page_icon="🧩", layout="wide")

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
            }
            .hero-word { font-size: 4.5rem; font-weight: 900; color: #1E88E5; line-height: 1.2; }
            .hero-phonetic { font-size: 1.5rem; color: #666; font-family: 'Inter'; margin-bottom: 1rem; }
            .vibe-box { background: #f0f7ff; border-left: 5px solid #1E88E5; padding: 20px; border-radius: 10px; }
            .operator { color: #BBDEFB; margin: 0 8px; }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 獨立資料庫 A：雲端百科 (20 欄)
# ==========================================
@st.cache_data(ttl=30)
def load_cloud_db():
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
# 3. 獨立資料庫 B：實驗室 (內置數據)
# ==========================================
def get_lab_data():
    data = [
        {"word": "neuromorphic", "p": "neuro", "r": "morphic", "definition": "類神經型態的", "vibe": "模擬大腦神經元結構。", "phonetic": "ˌnjʊəroʊˈmɔːrfɪk"},
        {"word": "hyperdimensional", "p": "hyper", "r": "dimensional", "definition": "高維空間的", "vibe": "大型語言模型的運算核心。", "phonetic": "ˌhaɪpərdɪˈmɛnʃənl"},
        {"word": "autopoietic", "p": "auto", "r": "poietic", "definition": "自我生成的", "vibe": "系統具備自我維護的生命力。", "phonetic": "ˌɔːtoʊpɔɪˈɛtɪk"}
    ]
    df = pd.DataFrame(data)
    return {
        "prefixes": [{"id": p, "label": f"{p}-"} for p in sorted(df['p'].unique())],
        "roots": [{"id": r, "label": f"-{r}"} for r in sorted(df['r'].unique())],
        "dictionary": data
    }

# ==========================================
# 4. 原有功能組件 (v2.5)
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

def show_encyclopedia_card(row):
    st.markdown(f"<div class='hero-word'>{row['word']}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='hero-phonetic'>/{row['phonetic']}/</div>", unsafe_allow_html=True)
    
    col_a, col_b = st.columns([1, 4])
    with col_a:
        if st.button("🔊 朗讀", key=f"spk_{row['word']}"): speak(row['word'], row['word'])
    with col_b:
        styled_breakdown = row['breakdown'].replace("+", "<span class='operator'>+</span>")
        st.markdown(f"<div class='breakdown-container'>{styled_breakdown}</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.info(f"**🎯 定義：**\n{row['definition']}")
        st.write(f"**📝 例句：**\n{row['example']}\n\n（{row['translation']}）")
    with c2:
        st.success(f"**💡 字根：** {row['roots']}\n\n**意義：** {row['meaning']}")
        st.markdown(f"**🪝 記憶：**\n{row['memory_hook']}")

    if row['native_vibe']:
        with st.expander("🌊 查看母語語感 (Native Vibe)"):
            st.markdown(f"<div class='vibe-box'>{row['native_vibe']}</div>", unsafe_allow_html=True)

# ==========================================
# 5. 新增：React 滾輪組件
# ==========================================
def render_react_lab(payload):
    json_data = json.dumps(payload)
    html_code = """
    <!DOCTYPE html><html><head>
        <script src="https://unpkg.com/react@18/umd/react.development.js"></script>
        <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
        <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            .no-scrollbar::-webkit-scrollbar { display: none; } 
            .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
            /* 優化遮罩：讓中間完全透明，確保文字清晰 */
            .mask { 
                background: linear-gradient(180deg, 
                    rgba(255,255,255,1) 0%, 
                    rgba(255,255,255,0) 30%, 
                    rgba(255,255,255,0) 70%, 
                    rgba(255,255,255,1) 100%); 
            }
        </style>
    </head>
    <body class="bg-transparent"><div id="root"></div>
    <script type="text/babel">
        const { useState, useRef, useEffect } = React;
        const DATA = REPLACE_ME;

        const Wheel = ({ items, onSelect, label, initialValue }) => {
            const ref = useRef(null);
            const itemHeight = 44; // 每個項目的高度

            // 初始化時滾動到正確位置
            useEffect(() => {
                if (ref.current) {
                    const index = items.findIndex(i => i.id === initialValue);
                    ref.current.scrollTop = index * itemHeight;
                }
            }, []);

            const handleScroll = () => {
                if (!ref.current) return;
                const idx = Math.round(ref.current.scrollTop / itemHeight);
                if(items[idx] && items[idx].id !== initialValue) {
                    onSelect(items[idx].id);
                }
            };

            return (
                <div className="flex flex-col items-center">
                    <div className="text-[10px] font-bold text-gray-400 mb-1 uppercase tracking-widest">{label}</div>
                    <div className="relative w-32 h-36 bg-white rounded-2xl shadow-inner border border-gray-200 overflow-hidden">
                        {/* 修正選中高亮框的位置與層級 */}
                        <div className="absolute top-[46px] left-0 w-full h-[44px] bg-blue-50 border-y border-blue-100 z-0"></div>
                        
                        <div 
                            ref={ref} 
                            onScroll={handleScroll} 
                            className="h-full overflow-y-scroll snap-y snap-mandatory no-scrollbar py-[46px] relative z-10"
                        >
                            {items.map(i => (
                                <div key={i.id} className="h-[44px] flex items-center justify-center snap-center font-bold text-gray-600 text-lg">
                                    {i.label}
                                </div>
                            ))}
                        </div>
                        {/* 遮罩放在最上層但允許點擊穿透 */}
                        <div className="absolute inset-0 mask pointer-events-none z-20"></div>
                    </div>
                </div>
            );
        };

        const App = () => {
            const [p, setP] = useState(DATA.prefixes[0].id);
            const [r, setR] = useState(DATA.roots[0].id);
            const match = DATA.dictionary.find(d => d.p === p && d.r === r);

            return (
                <div className="flex flex-col items-center p-4">
                    <div className="flex items-center gap-4 mb-10">
                        <Wheel items={DATA.prefixes} onSelect={setP} label="Prefix" initialValue={p} />
                        <div className="text-3xl text-gray-300 mt-6">+</div>
                        <Wheel items={DATA.roots} onSelect={setR} label="Root" initialValue={r} />
                    </div>
                    {match ? (
                        <div className="w-full bg-white p-8 rounded-[2.5rem] shadow-2xl border border-blue-50 transition-all duration-300">
                            <h1 className="text-5xl font-black text-blue-600 mb-2 leading-tight">{match.word}</h1>
                            <p className="text-gray-400 font-mono mb-6 text-xl">/{match.phonetic}/</p>
                            <div className="bg-blue-50 p-5 rounded-2xl text-blue-900 font-bold text-lg mb-4">{match.definition}</div>
                            <p className="italic text-gray-500 font-medium">"{match.vibe}"</p>
                        </div>
                    ) : (
                        <div className="w-full h-32 flex flex-col items-center justify-center border-2 border-dashed border-gray-100 rounded-[2.5rem] bg-gray-50/50">
                            <span className="text-gray-300 italic">No Combination Found</span>
                            <span className="text-[10px] text-gray-200 mt-2 font-mono uppercase tracking-widest">{p} + {r}</span>
                        </div>
                    )}
                </div>
            );
        };
        ReactDOM.createRoot(document.getElementById('root')).render(<App />);
    </script></body></html>
    """.replace("REPLACE_ME", json_data)
    components.html(html_code, height=650)
# ==========================================
# 6. 主頁面邏輯
# ==========================================
def main():
    inject_custom_css()
    df = load_cloud_db()
    
    st.sidebar.title("Etymon Decoder")
    # 原有選單 + 新窗口「🧪 實驗室」
    page = st.sidebar.radio("功能選單", ["首頁", "學習與搜尋", "測驗模式", "🧪 組合實驗室"])
    st.sidebar.markdown("---")
    st.sidebar.caption("v2.5 Hybrid | 2026")

    if page == "首頁":
        st.markdown("<h1 style='text-align: center;'>Etymon Decoder</h1>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("📚 雲端單字", len(df))
        c2.metric("🏷️ 分類主題", df['category'].nunique() if not df.empty else 0)
        c3.metric("🧩 獨特字根", df['roots'].nunique() if not df.empty else 0)
        st.info("👈 左側選單可切換原有功能，或進入全新的『組合實驗室』。")

    elif page == "學習與搜尋":
        # 完全保留你原本的搜尋與隨機邏輯
        tab_card, tab_list = st.tabs(["🎲 隨機探索", "🔍 資料庫列表"])
        with tab_card:
            cats = ["全部"] + sorted(df['category'].unique().tolist())
            sel_cat = st.selectbox("選擇分類", cats)
            f_df = df if sel_cat == "全部" else df[df['category'] == sel_cat]
            if st.button("下一個 ➔"):
                st.session_state.curr_w = f_df.sample(1).iloc[0].to_dict()
            if 'curr_w' in st.session_state:
                show_encyclopedia_card(st.session_state.curr_w)
        with tab_list:
            search = st.text_input("🔍 搜尋...")
            mask = df.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)
            st.dataframe(df[mask][['word', 'definition', 'roots']], use_container_width=True)

    elif page == "測驗模式":
        # 保留測驗邏輯
        if not df.empty:
            if st.button("🎲 抽題"):
                st.session_state.q = df.sample(1).iloc[0].to_dict()
                st.session_state.show_ans = False
            if 'q' in st.session_state:
                st.info(st.session_state.q['definition'])
                if st.button("揭曉"): st.session_state.show_ans = True
                if st.session_state.get('show_ans'):
                    st.success(f"答案：{st.session_state.q['word']}")

    elif page == "🧪 組合實驗室":
        st.title("🧪 Etymon Mix Lab")
        st.write("這是獨立的實驗窗口，使用內置的 React 滾輪資料庫。")
        render_react_lab(get_lab_data())

if __name__ == "__main__":
    main()
