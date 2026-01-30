import streamlit as st

# --- 1. 定義通用 XYZ 邏輯函數 ---
def x_y_z_logic(x_idx, y_idx, z_idx, data_pool):
    """
    x_idx: 1=X, 2=Y, 3=Z (主體)
    y_idx: 1=a, 2=b, 3=c (成分)
    z_idx: 層指示器 (維度)
    """
    # 建立唯一的座標索引鍵值
    node_key = f"x{x_idx}_y{y_idx}"
    
    # 從資料池獲取原始數值 (預設為 1.0)
    # 對應筆記中的 a, b, c
    val = data_pool.get(node_key, 1.0)
    
    # 假設權重 x = 1 (可擴充)
    weight_x = 1.0
    
    if z_idx == 1:
        # Z=1: 基礎分量層 (例如 Xa, Xb, Xc)
        return f"分量值: {val * weight_x:.2f}"
    
    elif z_idx == 2:
        # Z=2: 打包層 (執行 X = ax + bx + cx)
        # 加總該 X 軸下所有的 Y 成分
        a_val = data_pool.get(f"x{x_idx}_y1", 1.0)
        b_val = data_pool.get(f"x{x_idx}_y2", 1.0)
        c_val = data_pool.get(f"x{x_idx}_y3", 1.0)
        package_x = (a_val + b_val + c_val) * weight_x
        return f"打包物件(X): {package_x:.2f}"
    
    elif z_idx == 3:
        # Z=3: 物理映射層 (對應 F=mvr)
        a_val = data_pool.get(f"x{x_idx}_y1", 1.0)
        b_val = data_pool.get(f"x{x_idx}_y2", 1.0)
        c_val = data_pool.get(f"x{x_idx}_y3", 1.0)
        m = (a_val + b_val + c_val)
        v, r = 3.0, 4.0 # 參考筆記中的係數
        force = m * v * r
        return f"物理出力(F): {force:.2f} N"

# --- 2. Streamlit 介面設計 ---
st.set_page_config(page_title="Pino XYZ Logic Cube", layout="wide")
st.title("Pino 邏輯系統：XYZ 座標演化模型")

# 初始化 Session State
if 'vault' not in st.session_state:
    st.session_state.vault = {}

# Z 軸指示器 (控制層級演化)
z_axis = st.select_slider(
    "Z 軸指示器 (層級深度)",
    options=[1, 2, 3],
    help="1: 基礎分量 | 2: 打包邏輯 | 3: 物理映射"
)

st.divider()

# --- 3. 生成 3x3 矩陣佈局 ---
# X 軸為欄，Y 軸為列
y_labels = {1: "a (核心/字首)", 2: "b (連結/字根)", 3: "c (邊界/詞尾)"} #
x_labels = {1: "X 軸主體", 2: "Y 軸主體", 3: "Z 軸主體"}

for y in range(1, 4):
    cols = st.columns(3)
    for x in range(1, 4):
        with cols[x-1]:
            with st.container(border=True):
                st.write(f"**座標 ({x}, {y}, {z_axis})**")
                st.caption(f"{x_labels[x]} - {y_labels[y]}")
                
                if z_axis == 1:
                    # 第一層提供輸入
                    input_key = f"x{x}_y{y}"
                    st.session_state.vault[input_key] = st.number_input(
                        "輸入分量值", 
                        value=1.0, 
                        key=f"input_{x}_{y}"
                    )
                else:
                    # 其他層顯示計算結果
                    result = x_y_z_logic(x, y, z_axis, st.session_state.vault)
                    st.info(result)

st.sidebar.markdown(f"""
### 當前維度說明
- **X 軸**: {x_labels[1]}...
- **Y 軸**: {y_labels[y]}...
- **Z 軸**: 當前處於第 **{z_axis}** 層
""")
