
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os
import sys

# Page Config
st.set_page_config(page_title="Polymarket Bot Dashboard", layout="wide")

# Sidebar
st.sidebar.title("🤖 Polymarket Bot")
page = st.sidebar.radio("Navigation", ["Live Trades", "Backtest Analysis", "Strategy Metrics"])

# Data Loading
@st.cache_data
def load_backtest_data():
    if os.path.exists("results/backtest_enhanced_v2_trades.csv"):
        return pd.read_csv("results/backtest_enhanced_v2_trades.csv")
    return None

def load_live_trades():
    if os.path.exists("data/polymarket_bot.db"):
        conn = sqlite3.connect("data/polymarket_bot.db")
        df = pd.read_sql_query("SELECT * FROM trades ORDER BY id DESC", conn)
        conn.close()
        return df
    return pd.DataFrame()

# Page 1: Live Trades
if page == "Live Trades":
    st.title("📡 Live Trading Monitor")
    
    df_live = load_live_trades()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Live Trades", len(df_live))
    
    if not df_live.empty:
        live_pnl = df_live['pnl'].sum()
        live_wr = len(df_live[df_live['result'] == 'WIN']) / len(df_live) * 100
        col2.metric("Live PnL", f"${live_pnl:.2f}")
        col3.metric("Win Rate", f"{live_wr:.1f}%")
        
        st.subheader("Recent Trades")
        st.dataframe(df_live.head(20))
        
        st.subheader("Equity Curve")
        df_live['timestamp'] = pd.to_datetime(df_live['timestamp'])
        df_live = df_live.sort_values('timestamp')
        df_live['equity'] = df_live['pnl'].cumsum()
        st.line_chart(df_live.set_index('timestamp')['equity'])
    else:
        st.info("No live trades recorded yet.")

# Page 2: Backtest Analysis
elif page == "Backtest Analysis":
    st.title("🧪 Backtest Results (V2 Enhanced)")
    
    df = load_backtest_data()
    
    if df is not None:
        # Metrics
        total_trades = len(df)
        win_rate = len(df[df['result'] == 'WIN']) / total_trades * 100
        total_pnl = df['pnl'].sum()
        roi = total_pnl * 100 # ROI per unit
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Trades", total_trades)
        col2.metric("Win Rate", f"{win_rate:.2f}%")
        col3.metric("Total PnL (Units)", f"{total_pnl:.2f}")
        col4.metric("ROI", f"{roi:.0f}%")
        
        # Charts
        st.subheader("Cumulative PnL")
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        df['equity'] = df['pnl'].cumsum()
        
        fig = px.line(df, x='timestamp', y='equity', title="Strategy Performance Over Time")
        st.plotly_chart(fig, use_container_width=True)
        
        # Hourly Heatmap
        st.subheader("Performance by Hour")
        hourly_perf = df.groupby('hour')['pnl'].sum().reset_index()
        fig2 = px.bar(hourly_perf, x='hour', y='pnl', title="PnL by Hour of Day", color='pnl')
        st.plotly_chart(fig2, use_container_width=True)
        
    else:
        st.error("Backtest data not found. Run `scripts/backtest_enhanced_v2.py` first.")

# Page 3: Strategy Metrics
elif page == "Strategy Metrics":
    st.title("📊 Strategy Health")
    
    st.markdown("""
    ### Current Configuration (Phase 4)
    - **Strategy**: Mean Reversion (RSI + EMA Trend)
    - **Volatility Filter**: Enabled (ATR check)
    - **Time-of-Day**: Asia Session Blocked (02:00 - 05:00 UTC)
    - **MTF Trend**: 1H Trend Confirmation
    """)
    
    st.info("Run `scripts/walk_forward_validation.py` to update robustness metrics.")
    
    if os.path.exists("results/walk_forward_results.csv"):
        df_wf = pd.read_csv("results/walk_forward_results.csv")
        st.subheader("Walk-Forward Stability")
        st.dataframe(df_wf)
        
        avg_pnl = df_wf['pnl'].mean()
        cv = df_wf['pnl'].std() / avg_pnl
        st.metric("Stability Score (CV)", f"{cv:.2f}", delta="Lower is Better" if cv < 1 else "Unstable", delta_color="inverse")
