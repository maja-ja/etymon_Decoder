import streamlit as st

# --- 通用處理函數 n_m_o ---
def n_m_o_logic(n, m, o, data_pool):
    """
    n: 欄座標, m: 列座標, o: 層指示器
    data_pool: 用來存放底層 a,b,c 數據的字典
    """
    key = f"{n}_{m}"
    # 獲取基礎元素 (如果不存在則設為 1)
    a = data_pool.get(f"{key}_a", 1.0)
    b = data_pool.get(f"{key}_b", 1.0)
    c = data_pool.get(f"{key}_c", 1.0)
    x = 1.2  # 假設的權重因子
    
    if o == 1:
        return f"元素態: a={a}, b={b}, c={c}"
    elif o == 2:
        # 執行打包邏輯: X = ax + bx + cx
        X_val = (a * x) + (b * x) + (c * x)
        return f"打包態 (X): {X_val:.2f}"
    else:
        # 執行物理映射 (o=3)
        X_val = (a * x) + (b * x) + (c * x)
        # 模擬筆記中的 F = m * v * r
        force = X_val * 9.8 
        return f"應用態 (F): {force:.2f} N"

# --- Streamlit UI ---
st.title("Pino 邏輯建模：X-Package 系統")

# 初始化 Session State 來儲存輸入的 a, b, c
if 'data' not in st.session_state:
    st.session_state.data = {}

# 層指示器 (控制 o)
o_layer = st.select_slider("滑動層指示器 (o): 觀察邏輯演化", options=[1, 2, 3])

# 建立 3x3 矩陣
rows, cols = 3, 3
for m in range(1, rows + 1):
    st_cols = st.columns(cols)
    for n in range(1, cols + 1):
        with st_cols[n-1]:
            with st.container(border=True):
                if o_layer == 1:
                    # 在第一層讓使用者輸入 a, b, c
                    st.write(f"輸入層 ({n},{m})")
                    key_prefix = f"{n}_{m}"
                    st.session_state.data[f"{key_prefix}_a"] = st.number_input("a", value=1.0, key=f"a_{n}_{m}")
                    st.session_state.data[f"{key_prefix}_b"] = st.number_input("b", value=1.0, key=f"b_{n}_{m}")
                else:
                    # 在其他層顯示打包或運算結果
                    result = n_m_o_logic(n, m, o_layer, st.session_state.data)
                    st.subheader(f"座標 ({n},{m})")
                    st.info(result)

st.markdown(f"**目前的 $o$ 層解釋：** " + 
            ("輸入基礎元素" if o_layer==1 else "執行 X = ax+bx+cx 打包" if o_layer==2 else "輸出物理映射結果"))
