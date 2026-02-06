# Polymarket/Crypto Mean Reversion Trading Bot 🤖

A robust, Python-based algorithmic trading system designed for **Mean Reversion** strategies on crypto markets (BTC/USDT). The project features a **unified architecture** where the live trading logic and backtesting strategy share the exact same source of truth.

## 🚀 Key Features

*   **Strategy**: "Strict Mean Reversion" using Dynamic RSI thresholds based on EMA Trend.
    *   **Logic**: Buy Low (Oversold) in Downtrends, Sell High (Overbought) in Uptrends.
    *   **Unified Source**: Strategy logic is centralized in `src/features/strategy.py`.
*   **Architecture**:
    *   **Live Bot**: `src/bot/` - Executes trades using the unified strategy.
    *   **Backtesting**: `scripts/backtest_*.py` - Simulates performance using the *exact same* strategy module.
    *   **Data**: Supports 1-minute OHLCV data from Binance (cached in `data/`).
*   **Performance**:
    *   Designed for high-frequency mean reversion (15m timeframe).
    *   Includes tools for analyzing "Worst Days" and recent performance.

## 📂 Project Structure

```
├── data/                       # Market data (CSV)
├── scripts/                    # Backtesting & Analysis Scripts
│   ├── backtest_last_30d_live.py   # Recent 30-day performance (Live Data)
│   ├── backtest_2y_comprehensive.py # Historical 2-Year Backtest
│   ├── backtest_2y_live_worst.py   # Stress Test (Top 10 Worst Days)
│   └── backtest_feb_1_to_5.py      # Ad-hoc analysis
├── src/
│   ├── bot/                    # Live Trading Bot Core
│   │   ├── main.py             # Execution Loop
│   │   └── features.py         # Feature Engineering (Imports Strategy)
│   └── features/
│       └── strategy.py         # UNIFIED STRATEGY LOGIC (Source of Truth)
├── results/                    # Backtest Reports & Logs
└── requirements.txt            # Python Dependencies
```

## �️ Usage

### 1. Setup
```bash
pip install -r requirements.txt
```

### 2. Run Backtests
**Check Recent Performance (Last 30 Days):**
```bash
python scripts/backtest_last_30d_live.py
```

**Run Stress Test (Find Worst Days):**
```bash
python scripts/backtest_2y_live_worst.py
```

**Run Historical Simulation (2 Years):**
```bash
python scripts/backtest_2y_comprehensive.py
```

### 3. Live Trading
(Requires API Keys in `.env`)
```bash
python src/bot/main.py
```

## 📊 Strategy Logic

The core strategy is defined in `src/features/strategy.py`:

**Indicators:**
*   **RSI (14)**: Momentum oscillator.
*   **EMA (50)**: Trend filter.

**Dynamic Thresholds:**
*   **Downtrend** (Price < EMA 50):
    *   Aggressive BUY: RSI < 38
    *   Standard SELL: RSI > 58
*   **Uptrend** (Price > EMA 50):
    *   Standard BUY: RSI < 43
    *   Aggressive SELL: RSI > 62

This logic is imported by both the Live Bot and Backtests to ensure parity.
