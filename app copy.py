import streamlit as st
import pandas as pd
import base64
import time
import json
from io import BytesIO
from gtts import gTTS

# ==========================================
# 1. 配置與雲端資料庫讀取 (支援 9 欄位架構)
# ==========================================
st.set_page_config(page_title="Kadowsella Open-Source v1.0", page_icon="🧩", layout="wide")

@st.cache_data(ttl=60)
def load_kadowsella_db():
    # 這是對應你提到的 9 欄位「單字架子」
    COL_NAMES = [
        'age', 'word', 'category', 'prefix', 'root', 
        'suffix', 'phonetic', 'visual_vibe', 'field_app'
    ]
    # 請替換成你開源的 Google Sheet ID
    SHEET_ID = "1W1ADPyf5gtGdpIEwkxBEsaJ0bksYldf4AugoXnq6Zvg"
    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv'
    
    try:
        df = pd.read_csv(url)
        # 如果欄位不足 9 個，自動補齊（避免程式崩潰）
        while len(df.columns) < 9:
            df[f"extra_{len(df.columns)}"] = ""
        df.columns = COL_NAMES[:len(df.columns)]
        return df.dropna(subset=['word']).fillna("未定義")
    except Exception as e:
        st.error(f"資料庫連線失敗: {e}")
        return pd.DataFrame(columns=COL_NAMES)

# ==========================================
# 2. 核心元件：Kadowsella 分齡解釋卡片
# ==========================================
def show_k_card(row):
    # 頂部：單字與讀音
    st.markdown(f"""
        <div style="background:#f8f9fa; padding:20px; border-radius:15px; border-left:10px solid #1E88E5;">
            <h1 style="color:#1E88E5; margin:0;">{row['word']}</h1>
            <p style="color:#666; font-size:1.2rem;">/{row['phonetic']}/ | 領域：{row['category']}</p>
        </div>
    """, unsafe_allow_html=True)

    # 中間：拆解流水線
    cols = st.columns(3)
    cols[0].metric("前綴 (Prefix)", row['prefix'])
    cols[1].metric("字根 (Root)", row['root'])
    cols[2].metric("後綴 (Suffix)", row['suffix'])

    st.markdown("---")
    
    # 核心：1號與2號 AI 磨合出的解釋
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"### 🖼️ {row['age']} 歲的畫面形容")
        st.info(row['visual_vibe'])
    with c2:
        st.markdown(f"### 🚀 {row['category']} 實際應用")
        st.success(row['field_app'])

# ==========================================
# 3. 主程式：加入年紀滾輪邏輯 (x+5)
# ==========================================
def main():
    st.sidebar.title("Kadowsella Protocol")
    st.sidebar.markdown("---")
    
    # 年齡區間選擇器 (體現你的 x+5 邏輯)
    age_step = st.sidebar.select_slider(
        "選擇學習年齡層 (x 歲)",
        options=[i for i in range(0, 101, 5)],
        value=15
    )
    
    df = load_kadowsella_db()
    
    # 過濾出當前年齡層的資料
    filtered_df = df[df['age'].astype(str) == str(age_step)]

    st.title(f"🧩 Kadowsella 解碼工廠 - {age_step} 歲區間")
    
    if filtered_df.empty:
        st.warning(f"目前資料庫中尚未建立 {age_step} 歲的解釋清單。正在等待 1 號 AI 生成中...")
    else:
        # 搜尋功能
        search = st.text_input("🔍 搜尋開源資料庫中的單字...")
        if search:
            display_df = filtered_df[filtered_df['word'].str.contains(search, case=False)]
        else:
            display_df = filtered_df

        if not display_df.empty:
            target_row = display_df.iloc[0] # 取搜尋到的第一個或當前第一個
            show_k_card(target_row)
            
            st.markdown("### 📊 該年齡層所有庫存")
            st.dataframe(display_df, use_container_width=True)

    # 底部開源宣告
    st.markdown("---")
    st.caption("Kadowsella v1.0 | Open Source Project | 本內容由 AI Multi-Agent 自動生成並經由分齡校正。")

if __name__ == "__main__":
    main()
