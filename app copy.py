import streamlit as st
import pandas as pd
import json
import base64
import random
from io import BytesIO
from gtts import gTTS
import streamlit.components.v1 as components

# ==========================================
# 1. 核心配置與 CSS
# ==========================================
st.set_page_config(page_title="Etymon Decoder Hybrid", page_icon="🧬", layout="wide")

def inject_custom_css():
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=Noto+Sans+TC:wght@500;700&display=swap');
            
            /* 全站字體 */
            .stApp { font-family: 'Inter', 'Noto Sans TC', sans-serif; }
            
            /* 調整 Streamlit 原生間距，讓 React 組件與下方內容更緊湊 */
            .block-container { padding-top: 2rem; }
            
            /* 裝飾性標題 */
            .section-title {
                font-size: 1.5rem;
                font-weight: 700;
                color: #1565C0;
                margin-top: 30px;
                margin-bottom: 15px;
                border-left: 5px solid #1E88E5;
                padding-left: 10px;
            }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 資料處理 (Python Brain)
# ==========================================
@st.cache_data(ttl=60)
def load_and_process_data():
    # 這裡模擬從 Google Sheets 讀取的資料 (你原本的 load_db 函式)
    # 為了演示，我們手動建立一個與 React 滾輪邏輯匹配的 DataFrame
    data = [
        {"word": "distract", "breakdown": "dis+tract", "roots": "tract", "meaning": "抽/拉", "definition": "使分心", "category": "心理", "native_vibe": "像是有東西把你拉離軌道", "phonetic": "dɪˈstrækt"},
        {"word": "transform", "breakdown": "trans+form", "roots": "form", "meaning": "形狀", "definition": "轉化/變形", "category": "變化", "native_vibe": "徹底的改變，像毛毛蟲變蝴蝶", "phonetic": "trænsˈfɔːrm"},
        {"word": "attract", "breakdown": "at+tract", "roots": "tract", "meaning": "抽/拉", "definition": "吸引", "category": "物理/人際", "native_vibe": "磁鐵般的引力", "phonetic": "əˈtrækt"},
        {"word": "predict", "breakdown": "pre+dict", "roots": "dict", "meaning": "說", "definition": "預測", "category": "時間", "native_vibe": "事情發生前就先說出來", "phonetic": "prɪˈdɪkt"},
        {"word": "revoke", "breakdown": "re+voke", "roots": "voke", "meaning": "喊叫", "definition": "撤銷", "category": "法律", "native_vibe": "把說出去的話喊回來", "phonetic": "rɪˈvoʊk"}
    ]
    df = pd.DataFrame(data)
    
    # --- 關鍵：為 React 準備數據結構 ---
    # 我們需要解析 breakdown (例如 "dis+tract") 來生成滾輪選項
    prefixes = set()
    roots = set()
    dictionary_map = []

    for _, row in df.iterrows():
        parts = row['breakdown'].split('+')
        if len(parts) >= 2:
            p, r = parts[0], parts[1]
            prefixes.add(p)
            roots.add(r)
            # 建立映射表供 React 查詢
            dictionary_map.append({
                "combo": [f"p_{p}", f"r_{r}", "none"], # 簡化版，暫不處理後綴
                "word": row['word'],
                "meaning": row['definition'],
                "display": f"{p} + {r}"
            })

    # 轉換成 React 需要的格式
    react_prefixes = [{"id": "none", "label": "---"}] + [{"id": f"p_{x}", "label": f"{x}-"} for x in sorted(list(prefixes))]
    react_roots = [{"id": f"r_{x}", "label": x} for x in sorted(list(roots))]
    # 這裡簡化後綴，你可以依樣畫葫蘆
    react_suffixes = [{"id": "none", "label": "---"}] 

    return df, {
        "prefixes": react_prefixes,
        "roots": react_roots,
        "suffixes": react_suffixes,
        "dictionary": dictionary_map
    }

def speak(text):
    try:
        tts = gTTS(text=text, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        audio_base64 = base64.b64encode(fp.getvalue()).decode()
        st.markdown(f'<audio src="data:audio/mp3;base64,{audio_base64}" autoplay></audio>', unsafe_allow_html=True)
    except: pass

# ==========================================
# 3. React 組件 (Frontend Skin)
# ==========================================
def render_react_wheel(react_data):
    # 將 Python 字典轉換為 JSON 字串，注入到 HTML 中
    json_data = json.dumps(react_data)
    
    html_code = f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <script src="https://unpkg.com/react@18/umd/react.development.js"></script>
        <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
        <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            .no-scrollbar::-webkit-scrollbar {{ display: none; }}
            .no-scrollbar {{ -ms-overflow-style: none; scrollbar-width: none; }}
            body {{ background-color: transparent; }} /* 讓背景透明融入 Streamlit */
            
            /* 滾輪選中時的動畫 */
            @keyframes highlight {{
                0% {{ transform: scale(1); }}
                50% {{ transform: scale(1.05); }}
                100% {{ transform: scale(1); }}
            }}
            .animate-pop {{ animation: highlight 0.3s ease-out; }}
        </style>
    </head>
    <body>
        <div id="root"></div>

        <script type="text/babel">
            const {{ useState, useEffect, useRef }} = React;

            // 接收來自 Python 的數據
            const DATA = {json_data};

            const Wheel = ({{ items, onSelect }}) => {{
                const containerRef = useRef(null);
                const handleScroll = () => {{
                    if (!containerRef.current) return;
                    const index = Math.round(containerRef.current.scrollTop / 60);
                    if (items[index]) onSelect(items[index].id);
                }};
                return (
                    <div className="relative w-24 h-[180px]">
                        <div ref={containerRef} onScroll={handleScroll} 
                             className="h-full overflow-y-scroll snap-y snap-mandatory no-scrollbar pt-[60px] pb-[60px]">
                            {{items.map((item, i) => (
                                <div key={i} className="h-[60px] flex items-center justify-center snap-center text-xl font-bold text-gray-700">
                                    {{item.label}}
                                </div>
                            ))}}
                        </div>
                    </div>
                );
            }};

            const App = () => {{
                // 預設選中第一個有效組合 (為了展示效果)
                const [sel, setSel] = useState([DATA.prefixes[1]?.id || "none", DATA.roots[0]?.id || "none", "none"]);
                const [match, setMatch] = useState(null);

                useEffect(() => {{
                    const found = DATA.dictionary.find(d => 
                        d.combo[0] === sel[0] && d.combo[1] === sel[1]
                    );
                    setMatch(found);
                }}, [sel]);

                return (
                    <div className="flex flex-col items-center justify-center p-2 space-y-6">
                        <div className="relative flex bg-white p-4 rounded-[30px] shadow-lg border-4 border-blue-100 overflow-hidden">
                            <div className="absolute top-1/2 left-0 w-full h-[60px] -translate-y-1/2 bg-blue-500/10 border-y-2 border-blue-500/30 pointer-events-none"></div>
                            <Wheel items={{DATA.prefixes}} onSelect={{id => setSel([id, sel[1], "none"])}} />
                            <div className="w-px bg-gray-100 h-32 my-auto"></div>
                            <Wheel items={{DATA.roots}} onSelect={{id => setSel([sel[0], id, "none"])}} />
                        </div>

                        {{match ? (
                            <div className="bg-gradient-to-r from-blue-600 to-blue-500 text-white p-6 rounded-2xl shadow-xl text-center w-full max-w-sm animate-pop">
                                <h1 className="text-3xl font-black tracking-wide">{{match.word}}</h1>
                                <p className="text-blue-100 text-sm mt-1">{{match.display}}</p>
                                <div className="mt-3 bg-white/20 py-1 px-3 rounded-full text-sm inline-block">
                                    {{match.meaning}}
                                </div>
                                <p className="mt-4 text-xs opacity-80">👇 往下捲動查看深度分析</p>
                            </div>
                        ) : (
                            <div className="h-24 flex items-center justify-center text-gray-400 border-2 border-dashed border-gray-300 rounded-2xl w-full max-w-sm">
                                試試轉動滾輪組合單字...
                            </div>
                        )}}
                    </div>
                );
            }};
            const root = ReactDOM.createRoot(document.getElementById('root'));
            root.render(<App />);
        </script>
    </body>
    </html>
    """
    # 渲染 HTML，高度設為 450px 以容納滾輪與卡片
    components.html(html_code, height=450)

# ==========================================
# 4. Streamlit 主程式 (The Deep Dive)
# ==========================================
def main():
    inject_custom_css()
    df, react_payload = load_and_process_data()

    # --- Header ---
    st.title("🧬 Etymon Decoder")
    st.markdown("**互動式語源解碼器**：請先在上方滾輪探索，找到感興趣的單字後，在下方進行深度解析。")

    # --- Part A: 互動前導 (React) ---
    with st.container():
        render_react_wheel(react_payload)

    st.write("---")

    # --- Part B: 深度百科 (Streamlit) ---
    st.markdown("<div class='section-title'>🔍 深度解析實驗室</div>", unsafe_allow_html=True)

    # 這裡是用戶從滾輪看到單字後，手動輸入或選擇的地方
    # (註：若要做到滾輪點擊後自動填入這裡，需要撰寫 Custom Component，這是 MVP 的折衷方案)
    
    col1, col2 = st.columns([2, 1])
    with col1:
        # 建立搜尋建議列表
        all_words = df['word'].tolist()
        selected_word = st.selectbox("請選擇或輸入上方解碼的單字：", all_words)
    
    with col2:
        st.write("") # Spacer
        st.write("") 
        if st.button("🚀 啟動深度分析", use_container_width=True, type="primary"):
            st.session_state.current_word = selected_word

    # 展示詳細卡片 (復用你之前的設計)
    if 'current_word' in st.session_state:
        word_data = df[df['word'] == st.session_state.current_word].iloc[0]
        
        # 這裡簡單重現你之前的卡片風格
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1E88E5, #1565C0); color: white; padding: 20px; border-radius: 15px; margin-top: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
            <div style="font-size: 2.5rem; font-weight: 800;">{word_data['word']}</div>
            <div style="font-size: 1rem; opacity: 0.8;">/{word_data['phonetic']}/</div>
            <div style="margin-top: 15px; font-size: 1.2rem;">
                <span style="background: rgba(255,255,255,0.2); padding: 5px 10px; border-radius: 5px;">{word_data['breakdown']}</span>
                <span style="margin-left: 10px;">= {word_data['definition']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.info(f"**💡 字根 ({word_data['roots']})：** {word_data['meaning']}")
            if st.button("🔊 朗讀發音"):
                speak(word_data['word'])
        with c2:
            with st.expander("🎁 語感驚喜包 (Native Vibe)", expanded=True):
                st.write(word_data['native_vibe'])

if __name__ == "__main__":
    main()