# app.py
import streamlit as st
import pandas as pd
from analyzer import analyze_stock
from tickers import TICKERS

st.set_page_config(layout="wide")

st.title("🚀 AI Trading System Pro")
st.caption("基于 9 EMA + 24 SMA 动态金叉趋势监控系统 | 顶级投行专供")

# 核心安全缓存拦截，10分钟内绝不重复刷雅虎服务器
@st.cache_data(ttl=600)
def run_scan():
    results = []
    for t in TICKERS:
        try:
            res = analyze_stock(t)
            if res:
                results.append(res)
        except:
            continue
    return pd.DataFrame(results)

if st.button("开始扫描", type="primary"):
    with st.spinner("数据安全通道开启中，正在本地内存解算指标..."):
        df = run_scan()

        if df.empty:
            st.warning("无有效数据，请检查网络或稍后再试。")
        else:
            # 统一按 Score 评分从高到低降序排列
            df = df.sort_values(by="Score", ascending=False).reset_index(drop=True)

            st.subheader("📊 全部量化扫描结果")
            
            # 自定义投行经典的红绿高亮样式
            def style_rows(val):
                if "金叉" in str(val) or "突破" in str(val):
                    return 'background-color: #e6f4ea; color: #137333; font-weight: bold;'
                if "死叉" in str(val) or "跌破" in str(val):
                    return 'background-color: #fce8e6; color: #c5221f; font-weight: bold;'
                return ''
                
            styled_df = df.style.map(style_rows, subset=['Signal & Breakout'])
            
            # 输出全宽完美看板
            st.dataframe(styled_df, use_container_width=True, height=600)

            # 提取前5名高分动能资产
            st.subheader("🔥 TOP 5 核心高分资产")
            st.dataframe(df.head(5), use_container_width=True)
