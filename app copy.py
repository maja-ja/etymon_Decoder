import streamlit as st
import pandas as pd
import base64
import time
import json
from io import BytesIO
from gtts import gTTS
import streamlit.components.v1 as components

# ==========================================
# 1. 核心配置與 CSS
# ==========================================
st.set_page_config(page_title="Etymon Decoder Hybrid", page_icon="🧩", layout="wide")

def inject_custom_css():
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=Noto+Sans+TC:wght@500;700&display=swap');
            
            /* 針對百科全書版的樣式 */
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
                box-shadow: 0 4px 15px rgba(30,136,229,0.3);
            }
            .hero-word { font-size: 4rem; font-weight: 900; color: #1E88E5; }
            .vibe-box {
                background-color: #f0f7ff;
                border-left: 5px solid #1E88E5;
                padding: 20px;
                border-radius: 10px;
                margin: 15px 0;
            }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 獨立資料庫 A：雲端百科版
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
    except:
        return pd.DataFrame(columns=COL_NAMES)

# ==========================================
# 3. 獨立資料庫 B：React 實驗室版 (內置)
# ==========================================
def get_lab_data():
    data = [
        {"word": "neuromorphic", "p": "neuro", "r": "morphic", "meaning": "形狀/型態", "definition": "類神經型態的", "vibe": "模擬大腦神經元結構的運算方式。", "phonetic": "ˌnjʊəroʊˈmɔːrfɪk"},
        {"word": "hyperdimensional", "p": "hyper", "r": "dimensional", "meaning": "維度/測量", "definition": "高維空間的", "vibe": "LLM 處理語義的核心邏輯。", "phonetic": "ˌhaɪpərdɪˈmɛnʃənl"},
        {"word": "autopoietic", "p": "auto", "r": "poietic", "meaning": "製作/創造", "definition": "自我生成的", "vibe": "系統具備自我演化的生命力。", "phonetic": "ˌɔːtoʊpɔɪˈɛtɪk"}
    ]
    df = pd.DataFrame(data)
    return {
        "prefixes": [{"id": p, "label": f"{p}-"} for p in sorted(df['p'].unique())],
        "roots": [{"id": r, "label": f"-{r}"} for r in sorted(df['r'].unique())],
        "dictionary": data # 簡化結構供 React 使用
    }

# ==========================================
# 4. 功能組件：語音 & React 渲染
# ==========================================
def speak(text):
    try:
        tts = gTTS(text=text, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        audio_base64 = base64.b64encode(fp.getvalue()).decode()
        st.components.v1.html(f'<audio autoplay="true" style="display:none;"><source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3"></audio>', height=0)
    except: pass

def render_react_lab(payload):
    json_data = json.dumps(payload)
    html_code = """
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://unpkg.com/react@18/umd/react.development.js"></script>
        <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
        <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            .no-scrollbar::-webkit-scrollbar { display: none; }
            .wheel-mask { background: linear-gradient(180deg, white 0%, transparent 30%, transparent 70%, white 100%); }
        </style>
    </head>
    <body class="bg-gray-50">
        <div id="root"></div>
        <script type="text/babel">
            const { useState, useEffect, useRef } = React;
            const DATA = REPLACE_ME;

            const Wheel = ({ items, onSelect, label }) => {
                const ref = useRef(null);
                return (
                    <div className="flex flex-col items-center">
                        <span className="text-[10px] uppercase tracking-tighter text-gray-400 mb-1">{label}</span>
                        <div className="relative w-28 h-32 bg-white rounded-xl shadow-inner border border-gray-200 overflow-hidden">
                            <div className="absolute top-[46px] w-full h-[40px] bg-blue-50 border-y border-blue-100 pointer-events-none"></div>
                            <div ref={ref} onScroll={() => {
                                const idx = Math.round(ref.current.scrollTop / 40);
                                if(items[idx]) onSelect(items[idx].id);
                            }} className="h-full overflow-y-scroll snap-y snap-mandatory no-scrollbar py-[46px]">
                                {items.map(item => (
                                    <div key={item.id} className="h-[40px] flex items-center justify-center snap-center font-bold text-gray-600">{item.label}</div>
                                ))}
                            </div>
                            <div className="absolute inset-0 wheel-mask pointer-events-none"></div>
                        </div>
                    </div>
                );
            };

            const App = () => {
                const [p, setP] = useState(DATA.prefixes[0].id);
                const [r, setR] = useState(DATA.roots[0].id);
                const match = DATA.dictionary.find(d => d.p === p && d.r === r);

                return (
                    <div className="p-4 max-w-xl mx-auto flex flex-col items-center">
                        <div className="flex items-center gap-4 mb-8">
                            <Wheel items={DATA.prefixes} onSelect={setP} label="Prefix" />
                            <div className="text-2xl text-gray-300 mt-4">+</div>
                            <Wheel items={DATA.roots} onSelect={setR} label="Root" />
                        </div>
                        {match ? (
                            <div className="w-full bg-white p-6 rounded-3xl shadow-xl border border-blue-50 animate-in fade-in slide-in-from-bottom-4">
                                <h1 className="text-4xl font-black text-blue-600 mb-1">{match.word}</h1>
                                <p className="text-gray-400 font-mono mb-4">/{match.phonetic}/</p>
                                <div className="space-y-3">
                                    <div className="bg-blue-50 p-4 rounded-xl">
                                        <p className="text-blue-800 font-bold">{match.definition}</p>
                                    </div>
                                    <p className="text-sm text-gray-500 italic">"{match.vibe}"</p>
                                </div>
                            </div>
                        ) : (
                            <div className="h-32 w-full border-2 border-dashed border-gray-200 rounded-3xl flex items-center justify-center text-gray-300">
                                No Combination Found
                            </div>
                        )}
                    </div>
                );
            };
            const root = ReactDOM.createRoot(document.getElementById('root'));
            root.render(<App />);
        </script>
    </body>
    </html>
    """.replace("REPLACE_ME", json_data)
    components.html(html_code, height=500)

# ==========================================
# 5. 主程式架構
# ==========================================
def main():
    inject_custom_css()
    
    # 側邊欄導航
    st.sidebar.title("Etymon Decoder")
    mode = st.sidebar.radio("切換系統模式", ["📚 百科全書 (Cloud)", "🧪 混合實驗室 (React)"])
    st.sidebar.markdown("---")

    if mode == "📚 百科全書 (Cloud)":
        df = load_cloud_db()
        st.title("📖 字源百科全書")
        
        # 這裡放入你第一個代碼的顯示邏輯 (show_encyclopedia_card 等)
        if not df.empty:
            word_list = df['word'].tolist()
            sel_w = st.selectbox("搜尋雲端單字", word_list)
            row = df[df['word'] == sel_w].iloc[0]
            
            # 顯示卡片
            st.markdown(f"<div class='hero-word'>{row['word']}</div>", unsafe_allow_html=True)
            if st.button("🔊 播放讀音"): speak(row['word'])
            
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**定義：** {row['definition']}")
                st.write(f"**例句：** {row['example']}")
            with col2:
                st.success(f"**字根：** {row['roots']}")
                st.write(f"**語感：** {row['native_vibe']}")
    
    else:
        st.title("🧪 混合拆解實驗室")
        st.write("轉動下方滾輪，即時組合獨立資料庫中的單字。")
        lab_payload = get_lab_data()
        render_react_lab(lab_payload)

if __name__ == "__main__":
    main()
