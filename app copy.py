import streamlit as st
import json
import os
import random
import pandas as pd
from gtts import gTTS
import base64
from io import BytesIO
from gtts import gTTS
from streamlit_gsheets import GSheetsConnection
# ==========================================
# 1. 修正語音發音 (確保有聲音且 autoplay)
# ==========================================
def speak(text):
    """修正版：移除複雜 JS，改用更穩定的 HTML5 播放方式"""
    try:
        tts = gTTS(text=text, lang='en')
        fp = BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        audio_base64 = base64.b64encode(fp.read()).decode()
        
        # 使用 markdown 注入一個帶有自動播放屬性的音訊標籤
        # b64 內容很長，建議用 unsafe_allow_html=True
        audio_html = f"""
            <audio autoplay="true">
                <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
            </audio>
        """
        # 建立一個暫時的 placeholder 來放置音訊，避免影響 UI 排版
        st.markdown(audio_html, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"語音錯誤: {e}")
# ==========================================
# 1. 核心配置與雲端同步
# ==========================================

# 這是你原本「唯讀」的單字庫資料來源
SHEET_ID = '1W1ADPyf5gtGdpIEwkxBEsaJ0bksYldf4AugoXnq6Zvg'
GSHEET_URL = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv'
PENDING_FILE = 'pending_data.json'
# 這是你要「寫入」回報的目標網址 (從 secrets 讀取)
FEEDBACK_URL = st.secrets.get("feedback_sheet_url")

@st.cache_data(ttl=600)
def load_db():
    # 改為 9 欄一組的範圍
    BLOCKS = ["A:I", "J:R", "S:AA", "AB:AJ", "AK:AS"]
    
    all_dfs = []
    for rng in BLOCKS:
        try:
            url = f"{GSHEET_URL}&range={rng}"
            df_part = pd.read_csv(url)
            df_part = df_part.dropna(how='all')
            if not df_part.empty:
                # 確保欄位剛好是 9 個
                df_part = df_part.iloc[:, :9]
                df_part.columns = [
                    'category', 'roots', 'meaning', 'word', 
                    'breakdown', 'definition', 'phonetic', 'example', 'translation'
                ]
                all_dfs.append(df_part)
        except:
            continue

    if not all_dfs: return []
    df = pd.concat(all_dfs, ignore_index=True)
    
    # 結構化處理 (此處新增 translation 欄位)
    structured_data = []
    df = df.dropna(subset=['category'])
    for cat_name, cat_group in df.groupby('category'):
        root_groups = []
        for (roots, meaning), group_df in cat_group.groupby(['roots', 'meaning']):
            vocabulary = []
            for _, row in group_df.iterrows():
                vocabulary.append({
                    "word": str(row['word']),
                    "breakdown": str(row['breakdown']),
                    "definition": str(row['definition']),
                    "phonetic": str(row['phonetic']) if pd.notna(row['phonetic']) else "",
                    "example": str(row['example']) if pd.notna(row['example']) else "",
                    "translation": str(row['translation']) if pd.notna(row['translation']) else ""
                })
            root_groups.append({
                "roots": [r.strip() for r in str(roots).split('/')],
                "meaning": str(meaning),
                "vocabulary": vocabulary
            })
        structured_data.append({"category": str(cat_name), "root_groups": root_groups})
    return structured_data
def save_feedback_to_gsheet(word, feedback_type, comment):
    try:
        # 1. 建立連線
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # 2. 強制不使用快取讀取資料 (ttl=0)
        df = conn.read(spreadsheet=FEEDBACK_URL, ttl=0)
        
        # 2. 建立新資料列
        new_row = pd.DataFrame([{
            "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "word": word,
            "type": feedback_type,
            "comment": comment,
            "status": "pending"
        }])
        
        # 3. 合併並更新
        updated_df = pd.concat([df, new_row], ignore_index=True)
        
        # 4. 執行寫入 (關鍵：這一步需要 Service Account 權限)
        conn.update(spreadsheet=FEEDBACK_URL, data=updated_df)
        
        st.success(f"✅ 單字「{word}」的回報已同步至雲端！")
        
    except Exception as e:
        # 如果還是噴錯，顯示更詳細的訊息
        st.error(f"❌ 雲端同步失敗。")
        st.info("請檢查 Streamlit Cloud 的 Secrets 是否已包含完整的 [connections.gsheets] 區段內容。")
        st.caption(f"錯誤詳情: {e}")
def get_stats(data):
    """計算單字總數"""
    if not data: return 0, 0
    total_words = sum(len(g.get('vocabulary', [])) for cat in data for g in cat.get('root_groups', []))
    return len(data), total_words
# ==========================================
# 2. 通用與專業區域組件
# ==========================================
def ui_domain_page(domain_data, title, theme_color, bg_color):
    st.title(title)
    if not domain_data:
        st.info("目前資料庫中尚未建立相關分類。")
        return

    # 提取字根
    root_map = {}
    for cat in domain_data:
        for group in cat.get('root_groups', []):
            label = f"{'/'.join(group['roots'])} ({group['meaning']})"
            if label not in root_map: root_map[label] = group
    
    selected_label = st.selectbox("選擇要複習的字根", sorted(root_map.keys()), key=title)
    
    if selected_label:
        group = root_map[selected_label]
        for v in group.get('vocabulary', []):
            with st.container():
                # 修改欄位比例，為回報按鈕留出空間
                col_word, col_play, col_report = st.columns([3, 1, 1])
                
                with col_word:
                    display_color = "#FFD700" if "法律" in title else theme_color
                    st.markdown(f'<div style="font-size: 2.2em; font-weight: bold; color: {display_color};">{v["word"]}</div>', unsafe_allow_html=True)
                
                with col_play:
                    if st.button("播放", key=f"v_{v['word']}_{title}"):
                        speak(v['word'])
                
                with col_report:
                    # 呼叫新建立的回報組件
                    ui_feedback_component(v['word'])
                
                # 這裡針對拆解 (breakdown) 使用金色與深色背景框
                st.markdown(f"""
                    <div style="margin-bottom: 15px;">
                        <span style="font-size: 1.1em; color: #888;">構造拆解：</span>
                        <span style="font-size: 1.6em; color: #FFD700; font-family: 'Courier New', monospace; font-weight: bold; background: #888; padding: 4px 12px; border-radius: 8px; border: 1px solid #FFD700; text-shadow: 1px 1px 2px black;">
                            {v['breakdown']}
                        </span>
                        <div style="font-size: 1.3em; color: #DDD; margin-top: 10px;"><b>中文定義：</b> {v['definition']}</div>
                    </div>
                    <hr style="border-color: #444;">
                """, unsafe_allow_html=True)
def ui_feedback_component(word):
    """單字錯誤回報彈窗"""
    with st.popover("錯誤回報"):
        st.write(f"回報單字：**{word}**")
        f_type = st.selectbox("錯誤類型", ["發音錯誤", "拆解有誤", "中文釋義錯誤", "分類錯誤", "其他"], key=f"err_type_{word}")
        f_comment = st.text_area("詳細說明", placeholder="請描述正確的資訊...", key=f"err_note_{word}")
        
        if st.button("提交回報", key=f"err_btn_{word}"):
            if f_comment.strip() == "":
                st.error("請填寫說明內容")
            else:
                save_feedback_to_gsheet(word, f_type, f_comment)
                st.success("感謝回報！管理員將會盡快修正。")
def ui_quiz_page(data):
    st.title("學習區 (Flashcards)")
    cat_options_map = {"全部練習": "全部練習"}
    cat_options_list = ["全部練習"]
    for c in data:
        w_count = sum(len(g['vocabulary']) for g in c['root_groups'])
        display_name = f"{c['category']} ({w_count} 字)"
        cat_options_list.append(display_name)
        cat_options_map[display_name] = c['category']

    selected_raw = st.selectbox("選擇練習範圍", sorted(cat_options_list))
    selected_cat = cat_options_map[selected_raw]

    if st.session_state.get('last_quiz_cat') != selected_cat:
        st.session_state.last_quiz_cat = selected_cat
        if 'flash_q' in st.session_state: del st.session_state.flash_q
        st.rerun()

    if 'flash_q' not in st.session_state:
        if selected_cat == "全部練習":
            pool = [{**v, "cat": c['category']} for c in data for g in c['root_groups'] for v in g['vocabulary']]
        else:
            pool = [{**v, "cat": c['category']} for c in data if c['category'] == selected_cat for g in c['root_groups'] for v in g['vocabulary']]
        
        if not pool: st.warning("此範圍無資料"); return
        st.session_state.flash_q = random.choice(pool)
        st.session_state.flipped = False
        st.session_state.voiced = False 

    q = st.session_state.flash_q
    
    # 單字卡片正面
    st.markdown(f"""
        <div style="text-align: center; padding: 50px; border: 3px solid #eee; border-radius: 25px; background: #fdfdfd; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <p style="color: #999; font-weight: bold;">[ {q['cat']} ]</p>
            <h1 style="font-size: 4.5em; margin: 0; color: #1E88E5;">{q['word']}</h1>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("查看答案", use_container_width=True): 
            st.session_state.flipped = True
    with col2:
        if st.button("播放發音", use_container_width=True):
            speak(q['word'])
    with col3:
        if st.button("➡️ 下一題", use_container_width=True): 
            if 'flash_q' in st.session_state: del st.session_state.flash_q
            st.rerun()

    # 答案翻開後的邏輯
    if st.session_state.get('flipped'):
        if not st.session_state.get('voiced'):
            speak(q['word'])
            st.session_state.voiced = True
            
        is_legal = "法律" in q['cat']
        bg_color = "#1A1A1A" if is_legal else "#E3F2FD"
        label_color = "#FFD700" if is_legal else "#1E88E5"
        text_color = "#FFFFFF" if is_legal else "#000000"
        breakdown_color = "#FFD700" if is_legal else "#D32F2F"

        # 處理音標：移除多餘斜線
        p_val = str(q.get('phonetic', '')).strip().replace('/', '')
        phonetic_html = f"<div style='color:{label_color}; font-size:1.2em; margin-bottom:5px;'>/{p_val}/</div>" if p_val and p_val != "nan" else ""
        
        # 處理例句與翻譯：直接組合成字串，不使用多行引號以減少錯誤
        e_val = str(q.get('example', '')).strip()
        t_val = str(q.get('translation', '')).strip()
        
        example_html = ""
        if e_val and e_val != "nan":
            # 這裡改用最簡單的字串相加，避免縮排問題
            example_html += f"<hr style='border-color:#555; margin:15px 0;'>"
            example_html += f"<div style='font-style:italic; color:#666; font-size:1.1em;'>{e_val}</div>"
            if t_val and t_val != "nan":
                example_html += f"<div style='color:#666; font-size:0.95em; margin-top:5px;'>({t_val})</div>"

        # 最終渲染：確保 full_html 變數完全左對齊，沒有任何空格縮排
        full_html = f"""
<div style="background-color:{bg_color}; padding:25px; border-radius:15px; border:1px solid {label_color}; border-left:10px solid {label_color}; margin-top:20px;">
{phonetic_html}
<div style="font-size:2em; margin-bottom:10px; color:{text_color};">
<strong style="color:{label_color};">拆解：</strong>
<span style="color:{breakdown_color}; font-family:monospace; font-weight:bold;">{q['breakdown']}</span>
</div>
<div style="font-size:1.5em; color:{text_color};">
<strong style="color:{label_color};">釋義：</strong> {q['definition']}
</div>
{example_html}
</div>
"""
        st.markdown(full_html, unsafe_allow_html=True)
def ui_search_page(data, selected_cat):
    st.title("搜尋與瀏覽")
    relevant = data if selected_cat == "全部顯示" else [c for c in data if c['category'] == selected_cat]
    query = st.text_input("搜尋單字或字根...").strip().lower()
    for cat in relevant:
        for group in cat.get('root_groups', []):
            matched = [v for v in group['vocabulary'] if query in v['word'].lower() or any(query in r.lower() for r in group['roots'])]
            if matched:
                with st.expander(f"{'/'.join(group['roots'])} ({group['meaning']})", expanded=bool(query)):
                    for v in matched:
                        st.markdown(f"**{v['word']}** [{v['breakdown']}]: {v['definition']}")
def ui_admin_page(data):
    st.title("🛡️ 管理區 (Cloud Admin)")
    
    # 1. 密碼驗證 (使用 st.secrets)
    correct_password = st.secrets.get("admin_password", "8787")
    if not st.session_state.get('admin_auth'):
        pw_input = st.text_input("管理員密碼", type="password")
        if pw_input == correct_password:
            st.session_state.admin_auth = True
            st.rerun()
        elif pw_input != "":
            st.error("密碼錯誤")
        return

    # 2. 數據統計
    st.metric("資料庫單字總量", f"{get_stats(data)[1]} 單字")
    
    # 3. 備份功能
    if st.button("手動備份 CSV (下載完整單字庫)"):
        flat = [{"category": c['category'], "roots": "/".join(g['roots']), "meaning": g['meaning'], **v} 
                for c in data for g in c['root_groups'] for v in g['vocabulary']]
        st.download_button("確認下載 CSV", pd.DataFrame(flat).to_csv(index=False).encode('utf-8-sig'), "etymon_backup.csv")

    st.divider()

    # 4. 讀取雲端回報 (取代舊的 PENDING_FILE 邏輯)
    st.subheader("📝 雲端待處理回報")
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # 使用你在 Section 1 定義的 FEEDBACK_URL
        df_pending = conn.read(spreadsheet=FEEDBACK_URL)
        
        if not df_pending.empty:
            st.dataframe(df_pending, use_container_width=True)
            
            st.info("💡 提示：如需修改或刪除回報，請直接前往 Google Sheets 進行操作。")
            if st.button("重新整理雲端數據"):
                st.rerun()
        else:
            st.info("目前沒有待處理的回報。")
    except Exception as e:
        st.error(f"讀取雲端回報失敗，請檢查 Service Account 權限與 FEEDBACK_URL。")
        st.caption(f"錯誤詳情: {e}")

    # 5. 登出
    if st.sidebar.button("登出管理區"):
        st.session_state.admin_auth = False
        st.rerun()
# ==========================================
# 3. 主程序入口
# ==========================================
def main():
    st.set_page_config(page_title="Etymon Decoder", layout="wide")
    data = load_db()
    
    # 1. 側邊欄標題
    st.sidebar.title("Etymon Decoder")
    
    # 2. 導覽選單 (只保留這一個，並帶有唯一的 key)
    menu = st.sidebar.radio(
        "導航", 
        ["字根區", "學習區", "國小區", "國中區", "高中區", "醫學區", "法律區", "人工智慧區", "心理與社會區", "生物與自然區", "管理區"],
        key="main_navigation"
    )
    
    st.sidebar.divider()
    
    # 3. 強制刷新按鈕
    if st.sidebar.button("強制刷新雲端數據", use_container_width=True): 
        st.cache_data.clear()
        st.rerun()
    
    # 4. 顯示單字總量統計
    _, total_words = get_stats(data)
    st.sidebar.markdown(f"""
        <div style="text-align: center; padding: 10px; background-color: #f0f2f6; border-radius: 10px; margin-top: 10px;">
            <p style="margin: 0; font-size: 0.9em; color: #000;">資料庫總計</p>
            <p style="margin: 0; font-size: 1.8em; font-weight: bold; color: #000;">{total_words} <span style="font-size: 0.5em;">Words</span></p>
        </div>
    """, unsafe_allow_html=True)

    # --- 各分頁呼叫邏輯 ---
    if menu == "字根區":
        cats = ["全部顯示"] + sorted(list(set(c['category'] for c in data)))
        ui_search_page(data, st.sidebar.selectbox("分類篩選", cats))
    
    elif menu == "學習區":
        ui_quiz_page(data)

    elif menu == "國小區":
        elem = [c for c in data if any(k in str(c.get('category','')) for k in ["國小", "Elementary"])]
        count = sum(len(g.get('vocabulary',[])) for c in elem for g in c.get('root_groups',[]))
        ui_domain_page(elem, f"國小基礎字根 ({count} 字)", "#FB8C00", "#FFF3E0")

    elif menu == "國中區":
        jhs = [c for c in data if any(k in str(c.get('category','')) for k in ["國中", "Junior"])]
        count = sum(len(g.get('vocabulary',[])) for c in jhs for g in c.get('root_groups',[]))
        ui_domain_page(jhs, f"國中基礎字根 ({count} 字)", "#00838F", "#E0F7FA")

    elif menu == "高中區":
        hs = [c for c in data if any(k in str(c.get('category','')) for k in ["高中", "7000"])]
        count = sum(len(g.get('vocabulary',[])) for c in hs for g in c.get('root_groups',[]))
        ui_domain_page(hs, f"高中核心字根 ({count} 字)", "#2E7D32", "#E8F5E9")

    elif menu == "醫學區":
        med = [c for c in data if "醫學" in str(c.get('category',''))]
        count = sum(len(g.get('vocabulary',[])) for c in med for g in c.get('root_groups',[]))
        ui_domain_page(med, f"醫學專業字根 ({count} 字)", "#C62828", "#FFEBEE")

    elif menu == "法律區":
        law = [c for c in data if "法律" in str(c.get('category',''))]
        count = sum(len(g.get('vocabulary',[])) for c in law for g in c.get('root_groups',[]))
        ui_domain_page(law, f"法律術語字根 ({count} 字)", "#FFD700", "#1A1A1A")

    elif menu == "人工智慧區":
        ai = [c for c in data if any(k in str(c.get('category','')) for k in ["人工智慧", "AI","資工"])]
        count = sum(len(g.get('vocabulary',[])) for c in ai for g in c.get('root_groups',[]))
        ui_domain_page(ai, f"人工智慧相關字根 ({count} 字)", "#1565C0", "#E3F2FD")

    elif menu == "心理與社會區":
        psy = [c for c in data if any(k in str(c.get('category','')) for k in ["心理", "社會", "Psych", "Soc"])]
        count = sum(len(g.get('vocabulary',[])) for c in psy for g in c.get('root_groups',[]))
        ui_domain_page(psy, f"心理與社會科學字根 ({count} 字)", "#AD1457", "#FCE4EC")

    elif menu == "生物與自然區":
        bio = [c for c in data if any(k in str(c.get('category','')) for k in ["生物", "自然", "科學", "Bio", "Sci"])]
        count = sum(len(g.get('vocabulary',[])) for c in bio for g in c.get('root_groups',[]))
        ui_domain_page(bio, f"生物與自然科學字根 ({count} 字)", "#2E7D32", "#E8F5E9")

    elif menu == "管理區":
        ui_admin_page(data)
if __name__ == "__main__":
    main()
