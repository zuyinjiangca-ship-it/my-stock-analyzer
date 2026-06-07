import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# 设置Streamlit页面为全宽模式（匹配老板给的模板风格）
st.set_page_config(layout="wide", page_title="Top Investment Bank - Daily Analyzer")

st.title("📊 投行核心资产日线（Daily）量化扫描器")
st.caption("专注 9 EMA + 24 SMA 动能交叉 | 布林带 | 斐波那契 | 实时量价追踪")

# 1. 自选股列表（基于您的模板）
DEFAULT_TICKERS = [
    "MCHP", "TXN", "GFS", "TSM", "AAOI", "NOK", "MU", "HIMX", 
    "ON", "STM", "NVTS", "COHR", "VPG", "ENPH", "AEHR", 
    "ANET", "BE", "CLS", "AVGO", "IREN", "ASX", "AMZN", "AMKR"
]

# 侧边栏配置
tickers_input = st.sidebar.text_area("输入日线监控股票代码:", ", ".join(DEFAULT_TICKERS))
tickers = [t.strip().upper() for t in tickers_input.replace("\n", ",").replace(" ", ",").split(",") if t.strip()]

# 2. 核心日线量化指标计算引擎
def calculate_daily_metrics(ticker):
    try:
        # 获取日线历史数据（6个月确保均线和斐波那契周期稳定）
        stock = yf.Ticker(ticker)
        df = stock.history(period="6m", interval="1d") # 严格限定为 Daily
        if df.empty or len(df) < 30:
            return None
        
        latest_close = df['Close'].iloc[-1]
        latest_vol = df['Volume'].iloc[-1]
        
        # A. 9 EMA 与 24 SMA 计算
        df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['SMA_24'] = df['Close'].rolling(window=24).mean()
        
        ema_9_now = df['EMA_9'].iloc[-1]
        sma_24_now = df['SMA_24'].iloc[-1]
        
        # B. 交叉信号判定 (追溯最近几天判定是否刚刚金叉/死叉)
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
        
        # D. 布林带 (20, 2)
        df['BB_mid'] = df['Close'].rolling(window=20).mean()
        df['BB_std'] = df['Close'].rolling(window=20).std()
        df['BB_lower'] = df['BB_mid'] - (2 * df['BB_std'])
        
        # E. 斐波那契回撤线（近60个交易日高低点）
        recent_df = df.tail(60)
        high_p = recent_df['High'].max()
        low_p = recent_df['Low'].min()
        diff = high_p - low_p
        fib_382 = high_p - 0.382 * diff
        fib_618 = high_p - 0.618 * diff
        
        # F. 动态支撑位与突破位置
        support = max(df['BB_lower'].iloc[-1], fib_618)
        resistance = fib_382
        
        if latest_close > resistance:
            breakout_status = " 🚀 突破阻力"
        elif latest_close < support:
            breakout_status = " ⚠️ 跌破支撑"
        else:
            breakout_status = ""
            
        # 融合突破状态到信号栏
        final_signal = trend_signal + breakout_status
        
        # G. 放量 / 缩量 判定（对比20日均量）
        df['Vol_SMA20'] = df['Volume'].rolling(window=20).mean()
        avg_vol = df['Vol_SMA20'].iloc[-1]
        if latest_vol > avg_vol * 1.5:
            vol_status = "🔥 放量"
        elif latest_vol < avg_vol * 0.7:
            vol_status = "💤 缩量"
        else:
            vol_status = "正常"
            
        # H. 基于 9EMA + 24SMA 的量化评分机制
        score = 50
        if trend_signal == "🎯 金叉启动": score += 25
        elif trend_signal == "📈 多头趋势": score += 15
        elif trend_signal == "🚨 死叉确立": score -= 25
        elif trend_signal == "📉 空头动能": score -= 15
        
        if "🚀 突破阻力" in final_signal: score += 15
        if vol_status == "🔥 放量" and "多头" in trend_signal: score += 10
        
        score = max(10, min(95, score)) # 确保分数在合理区间

        return {
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
        }
    except Exception as e:
        return None

# 3. 渲染数据表格
if st.sidebar.button("同步日线行情", type="primary"):
    with st.spinner("正在加载日线数据..."):
        results = []
        for t in tickers:
            res = calculate_daily_metrics(t)
            if res:
                results.append(res)
                
        if results:
            summary_df = pd.DataFrame(results)
            # 按 Score 降序排列，完全还原您的看板模板
            summary_df = summary_df.sort_values(by="Score", ascending=False).reset_index(drop=True)
            
            # 视觉样式增强
            def style_rows(val):
                if "金叉" in str(val) or "突破" in str(val):
                    return 'background-color: #e6f4ea; color: #137333; font-weight: bold;'
                if "死叉" in str(val) or "跌破" in str(val):
                    return 'background-color: #fce8e6; color: #c5221f; font-weight: bold;'
                return ''
                
            styled_df = summary_df.style.map(style_rows, subset=['Signal & Breakout'])
            
            st.dataframe(styled_df, use_container_width=True, height=750)
            st.success(f"日线扫描完成。当前监控资产：{len(summary_df)} 只")
        else:
            st.error("数据获取失败，请检查网络或代码列表。")