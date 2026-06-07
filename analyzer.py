# analyzer.py
import yfinance as yf
import pandas as pd
import numpy as np
import requests

def get_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    })
    return session

def analyze_stock(ticker):
    try:
        session = get_session()
        stock = yf.Ticker(ticker, session=session)
        df = stock.history(period="6m", interval="1d")

        if df.empty or len(df) < 30:
            return None

        latest_close = df['Close'].iloc[-1]
        latest_vol = df['Volume'].iloc[-1]

        # 1. 9 EMA 与 24 SMA 计算
        df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['SMA_24'] = df['Close'].rolling(window=24).mean()
        
        ema_9_now = df['EMA_9'].iloc[-1]
        sma_24_now = df['SMA_24'].iloc[-1]
        ema_9_prev = df['EMA_9'].iloc[-2]
        sma_24_prev = df['SMA_24'].iloc[-2]

        # 趋势信号判定
        if ema_9_prev < sma_24_prev and ema_9_now >= sma_24_now:
            trend_signal = "🎯 金叉启动"
        elif ema_9_prev > sma_24_prev and ema_9_now <= sma_24_now:
            trend_signal = "🚨 死叉确立"
        elif ema_9_now > sma_24_now:
            trend_signal = "📈 多头趋势"
        else:
            trend_signal = "📉 空头动能"

        # 2. RSI (14)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        latest_rsi = rsi.iloc[-1]

        # 3. 布林带 (20, 2)
        df['BB_mid'] = df['Close'].rolling(window=20).mean()
        df['BB_std'] = df['Close'].rolling(window=20).std()
        df['BB_lower'] = df['BB_mid'] - (2 * df['BB_std'])

        # 4. 斐波那契回撤线（近60交易日）
        recent_df = df.tail(60)
        high_p = recent_df['High'].max()
        low_p = recent_df['Low'].min()
        diff = high_p - low_p
        fib_382 = high_p - 0.382 * diff
        fib_618 = high_p - 0.618 * diff

        # 5. 动态支撑位与突破位置
        support = max(df['BB_lower'].iloc[-1], fib_618)
        resistance = fib_382

        if latest_close > resistance:
            breakout_status = " 🚀 突破阻力"
        elif latest_close < support:
            breakout_status = " ⚠️ 跌破支撑"
        else:
            breakout_status = ""
            
        final_signal = trend_signal + breakout_status

        # 6. 放量 / 缩量判定
        df['Vol_SMA20'] = df['Volume'].rolling(window=20).mean()
        avg_vol = df['Vol_SMA20'].iloc[-1]
        if latest_vol > avg_vol * 1.5:
            vol_status = "🔥 放量"
        elif latest_vol < avg_vol * 0.7:
            vol_status = "💤 缩量"
        else:
            vol_status = "正常"

        # 7. 量化评分机制
        score = 50
        if trend_signal == "🎯 金叉启动": score += 25
        elif trend_signal == "📈 多头趋势": score += 15
        elif trend_signal == "🚨 死叉确立": score -= 25
        elif trend_signal == "📉 空头动能": score -= 15
        if "🚀 突破阻力" in final_signal: score += 15
        if vol_status == "🔥 放量" and "多头" in trend_signal: score += 10
        score = max(10, min(95, score))

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
    except:
        return None