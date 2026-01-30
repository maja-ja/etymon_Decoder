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
# 1. 核心配置與視覺美化 (CSS)
# ==========================================
st.set_page_config(page_title="Etymon Decoder Hybrid", page_icon="🧬", layout="wide")

def inject_custom_css():
    st.markdown("""
        <style>
            /* 1. 核心字體 */
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=Noto+Sans+TC:wght@500;700&display=swap');

            .breakdown-container {
                font-family: 'Inter', 'Noto Sans TC', sans-serif; 
                font-size: 1.8rem !important; 
                font-weight: 700;
                letter-spacing: 1px;
                background: linear-gradient(135deg, #1E88E5 0%, #1565C0 100%);
                color: #FFFFFF;
                padding: 12px 30px;
                border-radius: 15px;
                display: inline-block;
                margin: 20px 0;
                box-shadow: 0 4px 15px rgba(30, 136, 229, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }

            .breakdown-container span.operator {
                color: #BBDEFB;
                margin: 0 8px;
            }
            
            /* Hero 樣式補強 */
            .hero-word {
                font-family: 'Inter', sans-serif;
                font-size: 3.5rem;
                font-weight: 800;
                color: #1E88E5;
                line-height: 1.2;
            }
            .hero-phonetic {
                font-family: 'Inter', monospace;
                font-size: 1.5rem;
                color: #546E7A;
                margin-bottom: 20px;
            }
            .vibe-box {
                background-color: #E3F2FD;
                border-left: 5px solid #2196F3;
                padding: 15px;
                border-radius: 8px;
                margin-top: 15px;
            }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 工具函式 (音訊、資料讀取、滾輪資料轉換)
# ==========================================

def speak(text, key_suffix=""):
    try:
        if not text: return
        tts = gTTS(text=text, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        audio_base64 = base64.b64encode(fp.getvalue()).decode()
        unique_id = f"audio_{int(time.time())}_{key_suffix}"
        st.components.v1.html(f'<audio id="{unique_id}" autoplay="true" style="display:none;"><source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3"></audio><script>document.getElementById("{unique_id}").play();</script>', height=0)
    except Exception as e: st.error(f"語音錯誤: {e}")

@st.cache_data(ttl=60)
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
        df = df.dropna(subset=['word']).fillna("").reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"資料庫連線失敗: {e}")
        return pd.DataFrame(columns=COL_NAMES)

def prepare_wheel_data(df):
    """將 DataFrame 轉換為 React 滾輪需要的 JSON 格式"""
    if df.empty:
        return {"prefixes": [], "roots": []}
    
    # 左輪：使用 Category (去重)
    cats = sorted(list(set(df['category'].astype(str).tolist())))
    prefixes = [{"id": c, "label": c[:8]} for c in cats if c] # 限制長度以免爆版
    
    # 右輪：使用 Roots (去重)
    roots_raw = sorted(list(set(df['roots'].astype(str).tolist())))
    roots = [{"id": r, "label": r} for r in roots_raw if r]
    
    return {"prefixes": prefixes, "roots": roots}

# ==========================================
# 3. React 滾輪組件 (嵌入版)
# ==========================================

def render_sidebar_wheel(payload):
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
            .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
            .wheel-mask {
                background: linear-gradient(180deg, rgba(255,255,255,1) 0%, rgba(255,255,255,0) 30%, rgba(255,255,255,0) 70%, rgba(255,255,255,1) 100%);
            }
            body { background-color: transparent; }
        </style>
    </head>
    <body>
        <div id="root"></div>
        <script type="text/babel">
            const { useState, useEffect, useRef } = React;
            const DATA = REPLACE_ME;

            const Wheel = ({ items, onSelect, currentId }) => {
                const ref = useRef(null);
                const handleScroll = () => {
                    if (!ref.current) return;
                    const idx = Math.round(ref.current.scrollTop / 36);
                    if (items[idx] && items[idx].id !== currentId) {
                        onSelect(items[idx].id);
                    }
                };
                return (
                    <div className="relative w-full h-28 bg-white rounded-lg shadow-inner border border-gray-200 overflow-hidden mb-1">
                        <div className="absolute top-[36px] left-0 w-full h-[36px] bg-blue-50 border-y border-blue-200 pointer-events-none"></div>
                        <div ref={ref} onScroll={handleScroll} className="h-full overflow-y-scroll snap-y snap-mandatory no-scrollbar py-[36px]">
                            {items.map((item, i) => (
                                <div key={i} className="h-[36px] flex items-center justify-center snap-center font-bold text-sm text-gray-500 truncate px-2">
                                    {item.label}
                                </div>
                            ))}
                        </div>
                        <div className="absolute inset-0 wheel-mask pointer-events-none"></div>
                    </div>
                );
            };

            const App = () => {
                const [p, setP] = useState(DATA.prefixes[0]?.id || "");
                const [r, setR] = useState(DATA.roots[0]?.id || "");

                return (
                    <div className="p-1 flex flex-col items-center w-full">
                        <div className="grid grid-cols-[1fr_20px_1fr] gap-1 w-full items-center">
                            <div className="flex flex-col items-center">
                                <span className="text-[10px] font-bold text-gray-400 mb-1 tracking-widest">CAT</span>
                                <Wheel items={DATA.prefixes} onSelect={setP} currentId={p} />
                            </div>
                            <div className="text-lg text-blue-400 font-light flex justify-center mt-4">×</div>
                            <div className="flex flex-col items-center">
                                <span className="text-[10px] font-bold text-gray-400 mb-1 tracking-widest">ROOT</span>
                                <Wheel items={DATA.roots} onSelect={setR} currentId={r} />
                            </div>
                        </div>
                        <div className="mt-2 text-[10px] text-gray-400 text-center w-full">
                            Spin to Mix • <span className="text-blue-500 font-bold">{p}</span> + <span className="text-blue-500 font-bold">{r}</span>
                        </div>
                    </div>
                );
            };

            const root = ReactDOM.createRoot(document.getElementById('root'));
            root.render(<App />);
        </script>
    </body>
    </html>
    """.replace("REPLACE_ME", json_data)
    components.html(html_code, height=200)

# ==========================================
# 4. 百科級顯示組件
# ==========================================

def show_encyclopedia_card(row):
    """美化顯示單一單字的百科卡片"""
    st.markdown(f"<div class='hero-word'>{row['word']}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='hero-phonetic'>/{row['phonetic']}/</div>", unsafe_allow_html=True)
    
    col_a, col_b = st.columns([1, 4])
    with col_a:
        if st.button("🔊 朗讀", key=f"spk_{row['word']}", use_container_width=True):
            speak(row['word'], row['word'])
    with col_b:
        styled_breakdown = row['breakdown'].replace("+", "<span class='operator'>+</span>")
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
        unlocked_key = f"unlocked_{row['word']}"
        if not st.session_state.get(unlocked_key, False):
            if st.button("🎁 拆開語感驚喜包 (Unlock Native Vibe)", use_container_width=True, type="secondary"):
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
# 5. 頁面邏輯
# ==========================================

def page_home(df):
    st.markdown("<h1 style='text-align: center;'>Etymon Decoder <span style='font-size:1rem;color:gray'>Hybrid</span></h1>", unsafe_allow_html=True)
    st.write("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("📚 總單字量", len(df))
    c2.metric("🏷️ 分類主題", df['category'].nunique())
    c3.metric("🧩 獨特字根", df['roots'].nunique())
    st.write("---")
    st.info("👈 左側 **Etymon Mixer** 已啟動！轉動滾輪探索分類與字根的無限可能，或從下方選單開始學習。")

def page_learn_search(df):
    st.title("📖 學習與搜尋")
    tab_card, tab_list = st.tabs(["🎲 隨機探索", "🔍 資料庫列表"])
    
    with tab_card:
        cats = ["全部"] + sorted(df['category'].unique().tolist())
        sel_cat = st.selectbox("選擇學習分類", cats)
        f_df = df if sel_cat == "全部" else df[df['category'] == sel_cat]

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

    if 'q' in st.session_state:
        st.markdown(f"### ❓ 請問這對應哪個單字？")
        st.info(st.session_state.q['definition'])
        st.write(f"**提示 (字根):** {st.session_state.q['roots']} ({st.session_state.q['meaning']})")
        
        if st.button("揭曉答案"):
            st.session_state.show_ans = True
        
        if st.session_state.show_ans:
            st.success(f"💡 答案是：**{st.session_state.q['word']}**")
            speak(st.session_state.q['word'], "quiz")
            st.write(f"結構拆解：`{st.session_state.q['breakdown']}`")

# ==========================================
# 6. 主程式 (Hybrid Architecture)
# ==========================================
def main():
    inject_custom_css()
    df = load_db()
    
    # --- Sidebar 混合區 ---
    with st.sidebar:
        st.markdown("### 🧬 Etymon Mixer")
        # 1. 準備動態資料
        wheel_data = prepare_wheel_data(df)
        # 2. 渲染 React 滾輪 (視覺裝飾與靈感)
        render_sidebar_wheel(wheel_data)
        st.caption("✨ Spin for Inspiration")
        st.markdown("---")
        
        # 3. 原有導航
        st.title("Navigation")
        page = st.radio("功能選單", ["首頁", "學習與搜尋", "測驗模式"])
        st.markdown("---")
        st.caption("v2.5 Hybrid Edition | 2026")

    # --- Main Content ---
    if df.empty:
        st.warning("資料庫目前是空的，請先在管理端完成雲端同步。")
        return

    if page == "首頁":
        page_home(df)
    elif page == "學習與搜尋":
        page_learn_search(df)
    elif page == "測驗模式":
        page_quiz(df)

if __name__ == "__main__":
    main()
