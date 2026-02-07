import requests
import pandas as pd
import numpy as np
import datetime

def fetch_binance_data():
    print("Fetching last 2000 minutes from Binance...")
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": "BTCUSDT",
        "interval": "1m",
        "limit": 1000  # Max per request
    }
    
    # Get 2 chunks to cover ~30 hours
    # Chunk 1 (Most recent)
    r1 = requests.get(url, params=params).json()
    
    # Chunk 2 (Older)
    end_time = r1[0][0] - 1
    params["endTime"] = end_time
    r2 = requests.get(url, params=params).json()
    
    data = r2 + r1 # Combine
    
    df = pd.DataFrame(data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "q_vol", "trades", "tb_base", "tb_quote", "ignore"
    ])
    
    df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms")
    df["close"] = df["close"].astype(float)
    df = df[["timestamp", "close"]].copy()
    return df

def run_strategy(df):
    print(f"\nRunning Backtest on {len(df)} candles...")
    print(f"Start: {df['timestamp'].iloc[0]}")
    print(f"End:   {df['timestamp'].iloc[-1]}")
    
    # Indicators
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi_14'] = 100 - (100 / (1 + rs))
    
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['dist_ema_50'] = df['close'] / df['ema_50'] - 1
    
    # Target (Results)
    df['future_close'] = df['close'].shift(-15)
    df['target'] = (df['future_close'] > df['close']).astype(int)
    
    # STRICT FILTER
    # Shift indicators to prevent look-ahead bias
    df['prev_rsi'] = df['rsi_14'].shift(1)
    df['prev_ema'] = df['ema_50'].shift(1)
    df['prev_close'] = df['close'].shift(1)
    df['dist_ema_50_prev'] = (df['prev_close'] / df['prev_ema']) - 1
    
    # STRICT FILTER
    df = df.dropna()
    df = df[df['timestamp'].dt.minute.isin([0, 15, 30, 45])].reset_index(drop=True)
    
    trades = []
    
    # Constants from Strategy
    FEES = 0.02
    ENTRY_PRICE = 0.50
    
    for i in range(len(df)):
        row = df.iloc[i]
        
        # Check for NaNs
        if pd.isna(row['prev_rsi']) or pd.isna(row['dist_ema_50_prev']):
            continue

        # Signals (Using PREVIOUS Closed Candle)
        rsi = row['prev_rsi']
        dist = row['dist_ema_50_prev']
        
        # 38/62 Thresholds (Aligned Strategy)
        rsi_buy = 35 if dist < 0 else 38
        rsi_sell = 65 if dist > 0 else 62
            
        signal = None
        if rsi < rsi_buy: signal = 'YES'
        elif rsi > rsi_sell: signal = 'NO'
        
        if not signal: continue
        
        # Outcome
        # Entry at Open, Exit at Close
        # Note: 'target' column is no longer needed/valid with the shift logic
        # We rely on the candle's explicit O/C
        
        won = (signal == 'YES' and row['close'] > row['open']) or (signal == 'NO' and row['close'] < row['open'])
        res_str = "WIN" if won else "LOSS"
        
        trades.append({
            "time": row['timestamp'],
            "signal": signal,
            "result": res_str
        })
        
    return trades

def print_results(trades):
    if not trades:
        print("No trades found in this period.")
        return

    print("\n" + "="*40)
    print("BACKTEST RESULTS (Last ~30 Hours)")
    print("="*40)
    
    wins = len([t for t in trades if t['result'] == 'WIN'])
    total = len(trades)
    win_rate = (wins/total) * 100
    
    print(f"Total Trades: {total}")
    print(f"Wins:         {wins}")
    print(f"Win Rate:     {win_rate:.1f}%")
    print("-" * 40)
    
    # PnL Scenarios
    # 1. Fixed $0.50 (Coin Flip)
    pnl_50 = wins * 0.48 - (total - wins) * 0.50 # 2% fee on win
    print(f"PnL @ $0.50 Entry: ${pnl_50:+.2f}")
    
    # 2. Limit $0.42 (Target)
    pnl_42 = wins * 0.56 - (total - wins) * 0.42 # (0.98 - 0.42) = 0.56
    print(f"PnL @ $0.42 Entry: ${pnl_42:+.2f}")
    print("="*40)

if __name__ == "__main__":
    df = fetch_binance_data()
    trades = run_strategy(df)
    print_results(trades)
