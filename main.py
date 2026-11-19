import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
 
st.set_page_config(page_title="FOREX SNIPER", layout="wide", page_icon="🎯")
 
# --- DARK SNIPER STYLE LIKE THE PHONE MOCKUP ---
st.markdown("""
<style>
.stApp { background-color: #0a0f1e; color: white; }
[data-testid="stSidebar"] { background-color: #11182e; }
h1, h2, h3 { color: white !important; }
div[data-testid="stMetric"] { background-color: #141d33; border: 1px solid #1fe0c5; border-radius: 12px; padding: 10px; }
div[data-testid="stMetric"] label { color: #9aa3b8 !important; }
div[data-testid="stMetric"] div { color: white !important; }
.stButton button { background-color: #1fe0c5 !important; color: black !important; font-weight: bold; border-radius: 10px; border: none; }
</style>
""", unsafe_allow_html=True)
 
if "symbol" not in st.session_state:
    st.session_state.symbol = "EURUSD=X"
if "monitoring" not in st.session_state:
    st.session_state.monitoring = False
 
st.sidebar.title("🎯 FOREX SNIPER")
page = st.sidebar.radio("Go to:", ["1. MAIN - Start Monitor", "2. DASHBOARD", "3. ECONOMIC CALENDAR"])
st.sidebar.divider()
st.session_state.symbol = st.sidebar.text_input("Type any symbol", value=st.session_state.symbol).strip().upper()
st.sidebar.caption("Examples: EURUSD=X, USDZAR=X, XAUUSD=X, BTC-USD, ETH-USD")
period = st.sidebar.selectbox("Period", ["1d", "5d", "1mo"], index=0)
interval = st.sidebar.selectbox("Interval", ["1m", "5m", "15m", "1h", "1d"], index=3)
 
def get_data(symbol, period, interval):
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if df is None or len(df) == 0:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df['EMA20'] = df['Close'].ewm(span=20).mean()
    df['EMA50'] = df['Close'].ewm(span=50).mean()
    df['TR'] = np.maximum(df['High']-df['Low'], np.maximum(abs(df['High']-df['Close'].shift(1)), abs(df['Low']-df['Close'].shift(1))))
    df['ATR'] = df['TR'].rolling(14).mean()
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss.replace(0, np.nan))))
    df['RSI'] = df['RSI'].fillna(50.0)
    last = df.iloc[-1]
    rsi = float(last['RSI']) if pd.notna(last['RSI']) else 50.0
    price = float(last['Close']); ema20=float(last['EMA20']); ema50=float(last['EMA50']); rsi=float(last['RSI']); atr=float(last['ATR'])
    if price > ema20 > ema50:
        signal = "🟢 BUY"
    elif price < ema20 < ema50:
        signal = "🔴 SELL"
    else:
        signal = "🟡 WAIT"
    if "BUY" in signal:
        sl = price - 1.5*atr; tp1 = price + 2*atr; tp2 = price + 3*atr
    elif "SELL" in signal:
        sl = price + 1.5*atr; tp1 = price - 2*atr; tp2 = price - 3*atr
    else:
        sl = price - 1.5*atr; tp1 = price + 2*atr; tp2 = price - 2*atr
    return df, price, ema20, ema50, rsi, atr, signal, sl, tp1, tp2
 
if page.startswith("1."):
    st.title("🎯 FOREX SNIPER - MAIN")
    st.caption("AI-Powered Forex Signals • Precision • Risk Managed")
    c1, c2, c3 = st.columns(3)
    if c1.button("▶️ START MONITOR", use_container_width=True):
        st.session_state.monitoring = True
    if c2.button("⏸️ STOP", use_container_width=True):
        st.session_state.monitoring = False
    if c3.button("🔄 REFRESH NOW", use_container_width=True):
        st.rerun()
    auto = st.checkbox("🔁 Auto-refresh every 60 seconds", value=True)
    if not st.session_state.monitoring:
        st.info("👆 Press START MONITOR to begin.")
        st.stop()
    @st.fragment(run_every=60 if auto else None)
    def show_live():
        result = get_data(st.session_state.symbol, period, interval)
        if result is None:
            st.error(f"No data for {st.session_state.symbol}")
            return
        df, price, ema20, ema50, rsi, atr, signal, sl, tp1, tp2 = result
        st.subheader(f"🔴 LIVE SNIPER SIGNAL - {st.session_state.symbol} - {signal}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Price", f"{price:.5f}")
        m2.metric("EMA 20", f"{ema20:.5f}")
        m3.metric("EMA 50", f"{ema50:.5f}")
        m4.metric("RSI", f"{rsi:.1f}")
        st.divider()
        st.subheader("🎯 Trade Plan")
        t1, t2, t3 = st.columns(3)
        t1.metric("🛑 STOP LOSS", f"{sl:.5f}")
        t2.metric("✅ TAKE PROFIT 1", f"{tp1:.5f}")
        t3.metric("✅ TAKE PROFIT 2", f"{tp2:.5f}")
        st.caption(f"ATR: {atr:.5f} | SL = 1.5x ATR, TP1 = 2x ATR, TP2 = 3x ATR | R:R 1:2")
        st.line_chart(df[['Close','EMA20','EMA50']])
        st.dataframe(df.tail(20))
        st.caption(f"Last updated: {time.strftime('%H:%M:%S')} - Auto-refresh: {'ON' if auto else 'OFF'}")
    show_live()
 
elif page.startswith("2."):
    st.title("📊 DASHBOARD - All Pairs")
    st.write("All symbols - Forex, Metals, Crypto, Indices, Stocks")
    if st.button("🔄 REFRESH DASHBOARD"):
        st.rerun()
    symbols = [
        "EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X", "AUDUSD=X", "USDCAD=X", "NZDUSD=X",
        "EURGBP=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X", "EURAUD=X", "EURCHF=X", "GBPCHF=X", "AUDCAD=X", "NZDJPY=X", "CADJPY=X", "CHFJPY=X", "EURCAD=X", "GBPCAD=X", "AUDNZD=X", "EURNZD=X", "GBPAUD=X",
        "USDZAR=X", "EURZAR=X", "GBPZAR=X", "USDMXN=X", "USDTRY=X", "USDBRL=X", "USDINR=X", "USDPLN=X", "USDSEK=X", "USDNOK=X", "USDSGD=X", "USDHKD=X",
        "XAUUSD=X", "XAGUSD=X", "GC=F", "SI=F", "CL=F", "BZ=F",
        "BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "DOGE-USD", "ADA-USD", "LTC-USD", "BNB-USD",
        "^DJI", "^GSPC", "^IXIC", "^FTSE", "^GDAXI",
        "AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "META"
    ]
    rows = []
    for s in symbols:
        try:
            r = get_data(s, "1d", "1h")
            if r:
                df, price, ema20, ema50, rsi, atr, signal, sl, tp1, tp2 = r
                rows.append({"Pair": s, "Price": round(price,5), "Signal": signal, "RSI": round(rsi,1), "SL": round(sl,5), "TP1": round(tp1,5), "TP2": round(tp2,5)})
        except:
            rows.append({"Pair": s, "Price": "-", "Signal": "Error", "RSI": "-", "SL": "-", "TP1": "-", "TP2": "-"})
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
    st.caption("Dashboard uses 1d / 1h. First load 30-45 sec - normal with 60+ symbols.")
 
else:
    st.title("📅 ECONOMIC CALENDAR")
    st.write("Don't trade 15 min before/after RED news.")
    st.warning("⚠️ Guide calendar. For live exact times, check ForexFactory.com")
    cal = pd.DataFrame([
        ["Mon", "09:30", "USD", "🔴", "US Retail Sales", "Moves USD pairs"],
        ["Tue", "10:00", "EUR", "🔴", "ECB President Speech", "Moves EURUSD"],
        ["Wed", "14:30", "USD", "🔴", "US CPI Inflation", "Biggest USD mover"],
        ["Thu", "14:30", "USD", "🟡", "US Jobless Claims", "Moves USD"],
        ["Fri", "14:30", "USD", "🔴", "US NFP Jobs Report", "Biggest move of month"],
        ["Fri", "16:00", "ZAR", "🟡", "SA Manufacturing", "Moves USDZAR"],
    ], columns=["Day", "Time (SAST)", "Currency", "Impact", "Event", "What it affects"])
    st.dataframe(cal, use_container_width=True)
    st.link_button("Open Live ForexFactory Calendar →", "https://www.forexfactory.com/calendar")
 
