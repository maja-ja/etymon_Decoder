import streamlit as st
import pandas as pd
import base64
import time
import json
from io import BytesIO
from gtts import gTTS

# ==========================================
# 1. 核心配置與 CSS
# ==========================================
st.set_page_config(page_title="Etymon Universe: New Era", page_icon="🧩", layout="wide")

def inject_custom_css():
    st.markdown("""
        <style>
            /* 保持你原本的 v2.5 視覺樣式 */
            .breakdown-container {
                font-family: 'Inter', 'Noto Sans TC', sans-serif; 
                font-size: 1.5rem !important; 
                background: linear-gradient(135deg, #1E88E5 0%, #1565C0 100%);
                color: #FFFFFF; padding: 12px 25px; border-radius: 12px;
                display: inline-block; margin: 10px 0;
            }
            .hero-word { font-size: 3.5rem; font-weight: 900; color: #1E88E5; }
            /* 自定義按鈕樣式 */
            div.stButton > button:first-child { border-radius: 10px; }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 獨立學科模組 (每個學科一個 def)
# ==========================================

# --- 國小模組 ---
def elem_chi(): st.title("🍎 國小國語"); st.info("新世代國語解碼邏輯載入中...")
def elem_eng(): st.title("🔤 國小英語"); st.info("新世代英語聽力模組載入中...")
def elem_mat(): st.title("🔢 國小數學"); st.info("新世代數學圖形模組載入中...")

# --- 國中模組 ---
def jun_chi(): st.title("📚 國中國文"); st.write("模組：文言文解構器")
def jun_eng(): st.title("🌍 國中英文"); st.write("模組：核心文法框架")
def jun_mat(): st.title("📐 國中數學"); st.write("模組：代數與幾何")
def jun_sci(): st.title("🧪 國中自然"); st.write("模組：理化生實驗室")
def jun_soc(): st.title("🏛️ 國中社會"); st.write("模組：史地整合系統")

# --- 高中模組 (完整 10 科) ---
def sen_chi(): st.title("🎭 高中國文"); st.success("高階文本思辨模組")
def sen_eng(): st.title("📑 高中英文"); st.success("學術寫作與閱讀解碼")
def sen_mat(): st.title("📉 高中數學"); st.success("微積分與統計分析")
def sen_bio(): st.title("🧬 高中生物"); st.success("分子生物與遺傳解碼")
def sen_che(): st.title("🧪 高中化學"); st.success("物質變化與有機化學")
def sen_esc(): st.title("🪐 高中地科"); st.success("天文與大氣科學")
def sen_phy(): st.title("⚡ 高中物理"); st.success("力學與電磁學實驗室")
def sen_geo(): st.title("🗺️ 高中地理"); st.success("空間資訊與地理系統")
def sen_his(): st.title("📜 高中歷史"); st.success("歷史脈絡與斷代分析")
def sen_civ(): st.title("⚖️ 高中公民"); st.success("法律、經濟與社會研究")

# ==========================================
# 3. 主導航與 Gateway
# ==========================================
def main():
    inject_custom_css()
    
    # 網址定義
    OLD_ERA_URL = "https://etymon-universe.streamlit.app/"
    
    # 初始化 Session State
    if 'current_universe' not in st.session_state:
        st.session_state.current_universe = "🏠 首頁"

    # --- 側邊欄：Era Gateway ---
    st.sidebar.title("Era Gateway")
    c1, c2 = st.sidebar.columns(2)
    with c1:
        # 使用 HTML 標籤確保跳轉不產生 Loop
        st.markdown(f'<a href="{OLD_ERA_URL}" target="_self"><button style="width:100%; border-radius:5px; border:1px solid #4B4B4B; background:none; color:white; padding:5px; cursor:pointer;">舊世代</button></a>', unsafe_allow_html=True)
    with c2:
        # 點擊新世代 = 回到本 App 的首頁
        if st.sidebar.button("新世代", use_container_width=True, type="primary"):
            st.session_state.current_universe = "🏠 首頁"
            st.rerun()

    st.sidebar.divider()

    # --- 三大主邏輯導覽 ---
    universe = st.sidebar.selectbox(
        "切換教育宇宙",
        ["🏠 首頁", "國小宇宙", "國中宇宙", "高中宇宙"],
        index=["🏠 首頁", "國小宇宙", "國中宇宙", "高中宇宙"].index(st.session_state.current_universe)
    )
    st.session_state.current_universe = universe

    # --- 頁面渲染分流 ---
    if universe == "🏠 首頁":
        st.title("✨ 新世代全學段解碼宇宙")
        st.markdown("""
        ### 您好，開發者。
        這裡已經根據您的需求將 **18 個學科** 徹底模組化。
        * **國小**：3 個模組
        * **國中**：5 個模組
        * **高中**：10 個模組 (包含生物、化學、物理、地科、歷、地、公)
        
        請從側邊欄選擇學段，並點擊上方按鈕切換科目。
        """)
        st.warning("覺得讀書不好玩？那就把學科變成你親手寫出來的程式模組吧。")

    elif universe == "國小宇宙":
        sub = st.radio("選擇學科", ["國語", "英語", "數學"], horizontal=True)
        maps = {"國語": elem_chi, "英語": elem_eng, "數學": elem_mat}
        st.divider()
        maps[sub]()

    elif universe == "國中宇宙":
        sub = st.radio("選擇學科", ["國文", "英文", "數學", "自然", "社會"], horizontal=True)
        maps = {"國文": jun_chi, "英文": jun_eng, "數學": jun_mat, "自然": jun_sci, "社會": jun_soc}
        st.divider()
        maps[sub]()

    elif universe == "高中宇宙":
        # 完整 10 科按鈕
        sub = st.radio(
            "選擇學科", 
            ["國文", "英文", "數學", "生物", "化學", "地科", "物理", "地理", "歷史", "公民"], 
            horizontal=True
        )
        maps = {
            "國文": sen_chi, "英文": sen_eng, "數學": sen_mat, "生物": sen_bio,
            "化學": sen_che, "地科": sen_esc, "物理": sen_phy, "地理": sen_geo,
            "歷史": sen_his, "公民": sen_civ
        }
        st.divider()
        maps[sub]()

if __name__ == "__main__":
    main()
