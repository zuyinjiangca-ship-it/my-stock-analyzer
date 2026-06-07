import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests

# 设置Streamlit页面为全宽模式
st.set_page_config(layout="wide", page_title="Top Investment Bank - Batch Analyzer")

st.title("📊 投行核心资产日线（Daily）量化扫描器")
st.caption("专注 9 EMA + 24 SMA 动能交叉 | 布林带 | 斐波那契 | 批量打包装载版 (极速防封锁)")

# 1. 自选股列表
DEFAULT_TICKERS = [
    "MCHP", "TXN", "GFS", "TSM", "AAOI", "NOK", "MU", "HIMX", 
    "ON", "STM", "NVTS", "COHR", "VPG", "ENPH", "AEHR", 
    "ANET", "BE", "CLS", "AVGO", "IREN", "ASX", "AMZN", "AMKR"
]

# 侧边栏配置
tickers_input = st.sidebar.text_area("输入日线监控股票代码:", ", ".join(DEFAULT_TICKERS))
processed_input = tickers_input.replace("\n", ",").replace(" ", ",").replace("\t", ",")
tickers = [t.strip().upper() for t in processed_input.split(",") if t.strip()]

# 创建安全面具 Session
@st.cache_resource
def get_hardened_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    })
    return session

# 2. 核心量化渲染与计算逻辑
if st.sidebar.button("同步日线行情", type="primary"):
    with st.spinner("🚀 正在启动批量数据引擎 (一键打包请求，绕过频控)..."):
        browser_session = get_hardened_session()
        
        # 🔥 关键改良：一次性下载所有股票的历史数据，只向雅虎服务器发送 1 次请求！
        try:
            raw_data = yf.download(
                tickers=tickers, 
                period="6m", 
                interval="1d", 
                session=browser_session, 
                group_by='ticker', # 按股票代码分组归类
                progress=False
            )
        except Exception as e:
            st.error(f"❌ 批量下载引擎连接失败: {str(e)}")
            raw_data = pd.DataFrame()

        if raw_data.empty:
            st.error("❌ 雅虎财经目前拒绝了云端服务器的批量请求。请稍等1-2分钟，或尝试减少自选股数量后重试。")
        else:
            results = []
            
            # 在本地内存中切片处理数据，不产生任何网络请求
            for ticker in tickers:
                try:
                    # 提取单只股票的 DataFrame
                    if len(tickers) == 1:
                        df = raw_data.copy()
                    else:
                        if ticker_cols := raw_data.get(ticker):
                            df = ticker_cols.copy()
                        else:
                            continue
                            
                    df = df.dropna(subset=['Close'])
                    if df.empty or len(df) < 30:
                        continue
                    
                    latest_close = df['Close'].iloc[-1]
                    latest_vol = df['Volume'].iloc[-1]
                    
                    # A. 9 EMA 与 24 SMA
                    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
                    df['SMA_24'] = df['Close'].rolling(window=24).mean()
                    
                    ema_9_now = df['EMA_9'].iloc[-1]
                    sma_24_now = df['SMA_24'].iloc[-1]
                    
                    # B. 趋势交叉判定
                    ema_9_prev = df['EMA_9'].iloc[-2]
                    sma_24_prev = df['SMA_24'].iloc[-2]
                    
                    if ema_9_prev < sma_24_prev and ema_9_now >= sma_24_now:
                        trend_signal = "🎯 金叉启动"
                    elif ema_9_prev > sma_24_prev and ema_9_now <= sma_24_now:
                        trend_signal = "🚨 死叉确立"
                    elif ema_9_now > sma_24_now:
                        trend_signal = "📈 多头趋势"
                    else:
                        trend_signal = "📉 空头动能"
                        
                    # C. RSI (14)
                    delta = df['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs))
                    latest_rsi = rsi.iloc[-1]
                    
                    # D. 布林带
                    df['BB_mid'] = df['Close'].rolling(window=20).mean()
                    df['BB_std'] = df['Close'].rolling(window=20).std()
                    df['BB_lower'] = df['BB_mid'] - (2 * df['BB_std'])
                    
                    # E. 斐波那契回撤
                    recent_df = df.tail(60)
                    high_p = recent_df['High'].max()
                    low_p = recent_df['Low'].min()
                    diff = high_p - low_p
                    fib_382 = high_p - 0.382 * diff
                    fib_618 = high_p - 0.618 * diff
                    
                    # F. 支撑与阻力
                    support = max(df['BB_lower'].iloc[-1], fib_618)
                    resistance = fib_382
                    
                    if latest_close > resistance:
                        breakout_status = " 🚀 突破阻力"
                    elif latest_close < support:
                        breakout_status = " ⚠️ 跌破支撑"
                    else:
                        breakout_status = ""
                        
                    final_signal = trend_signal + breakout_status
                    
                    # G. 放量 / 缩量
                    df['Vol_SMA20'] = df['Volume'].rolling(window=20).mean()
                    avg_vol = df['Vol_SMA20'].iloc[-1]
                    if latest_vol > avg_vol * 1.5:
                        vol_status = "🔥 放量"
                    elif latest_vol < avg_vol * 0.7:
                        vol_status = "💤 缩量"
                    else:
                        vol_status = "正常"
                        
                    # H. 评分
                    score = 50
                    if trend_signal == "🎯 金叉启动": score += 25
                    elif trend_signal == "📈 多头趋势": score += 15
                    elif trend_signal == "🚨 死叉确立": score -= 25
                    elif trend_signal == "📉 空头动能": score -= 15
                    if "🚀 突破阻力" in final_signal: score += 15
                    if vol_status == "🔥 放量" and "多头" in trend_signal: score += 10
                    score = max(10, min(95, score))

                    results.append({
                        "Ticker": ticker,
                        "Price": round(latest_close, 2),
                        "Score": int(score),
                        "9 EMA": round(ema_9_now, 2),
                        "24 SMA": round(sma_24_now, 2),
                        "Support": round(support, 2),
                        "Resistance": round(resistance, 2),
                        "RSI": round(latest_rsi, 1),
                        "Volume Status": vol_status,
                        "Signal & Breakout": final_signal
                    })
                except Exception:
                    continue # 个别无数据标的自动跳过，不加重服务器负担
            
            if results:
                summary_df = pd.DataFrame(results)
                summary_df = summary_df.sort_values(by="Score", ascending=False).reset_index(drop=True)
                
                def style_rows(val):
                    if "金叉" in str(val) or "突破" in str(val):
                        return 'background-color: #e6f4ea; color: #137333; font-weight: bold;'
                    if "死叉" in str(val) or "跌破" in str(val):
                        return 'background-color: #fce8e6; color: #c5221f; font-weight: bold;'
                    return ''
                    
                styled_df = summary_df.style.map(style_rows, subset=['Signal & Breakout'])
                st.dataframe(styled_df, use_container_width=True, height=750)
                st.success(f"📊 批量同步成功。当前监控核心资产：{len(summary_df)} 只")
            else:
                st.warning("⚠️ 提取到零个有效资产数据，请检查美股代码是否处于停牌状态。")
