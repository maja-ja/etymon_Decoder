import streamlit as st

# --- 核心邏輯函數：座標完全對齊圖片 ---
def n_m_o_logic(n_col, m_row, o_layer, data_vault):
    """
    n_col (1,2,3): 對應圖片上方的 a, b, c (垂直貫穿線)
    m_row (1,2,3): 對應圖片左側的 X, Y, Z (水平線)
    o_layer (1,2,3): Z軸深度 (o層)
    """
    # 建立與圖片位置一致的索引鍵
    key = f"m{m_row}_n{n_col}"
    val = data_vault.get(key, 1.0) # 獲取基礎 a,b,c 分量
    
    if o_layer == 1:
        # Z=1: 基礎元素交點 (如圖片左上的 ax, bx, cx)
        return f"分量值: {val:.2f}"
    
    elif o_layer == 2:
        # Z=2: 打包邏輯 (X = ax + bx + cx)
        # 橫向加總：抓取同一個 m_row 下的所有 n_col
        ax = data_vault.get(f"m{m_row}_n1", 1.0)
        bx = data_vault.get(f"m{m_row}_n2", 1.0)
        cx = data_vault.get(f"m{m_row}_n3", 1.0)
        package_result = ax + bx + cx
        return f"打包總和: {package_result:.2f}"
    
    elif o_layer == 3:
        # Z=3: 物理映射 (根據 IMG_1561 的 F = m * 3 * v...)
        # 以打包後的結果作為質量 m
        mass = data_vault.get(f"m{m_row}_n1", 1.0) + \
               data_vault.get(f"m{m_row}_n2", 1.0) + \
               data_vault.get(f"m{m_row}_n3", 1.0)
        v, r = 3.0, 4.0 
        force = mass * v * r
        return f"物理出力: {force:.2f} N"

# --- UI 佈局設定 ---
st.set_page_config(layout="wide")
st.title("Pino 邏輯立方體 (手稿對齊版)")

if 'vault' not in st.session_state:
    st.session_state.vault = {}

# 層指示器 (控制 o)
o_depth = st.select_slider("滑動控制 Z 軸 (o 層)", options=[1, 2, 3])

st.divider()

# --- 根據圖片生成的 3x3 矩陣 ---
m_labels = {1: "X 行", 2: "Y 行", 3: "Z 行"}
n_labels = {1: "a 欄", 2: "b 欄", 3: "c 欄"}

# 建立表格：外層迴圈為列 (m)，內層為欄 (n)
for m in range(1, 4):
    cols = st.columns(3)
    for n in range(1, 4):
        with cols[n-1]:
            with st.container(border=True):
                st.write(f"**座標 ({n}, {m}, {o_depth})**")
                st.caption(f"{m_labels[m]}{n_labels[n]}")
                
                if o_depth == 1:
                    # 第一層：手動輸入分量 (ax, ay, az...)
                    input_key = f"m{m}_n{n}"
                    st.session_state.vault[input_key] = st.number_input(
                        "分量數值", value=1.0, key=f"in_{m}_{n}"
                    )
                else:
                    # 後續層：自動運算
                    result = n_m_o_logic(n, m, o_depth, st.session_state.vault)
                    st.info(result)

st.sidebar.info(f"當前觀測：{('分量層' if o_depth==1 else '打包層' if o_depth==2 else '物理映射層')}")
