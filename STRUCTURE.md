# Project Structure

## Overview
This repository follows a simplified, **domain-driven architecture** focused on ensuring parity between Live Trading and Backtesting.

## Directory Layout

### `src/` (Core Logic)
*   **`bot/`**: Contains the live trading execution engine.
    *   `main.py`: The entry point for the live/paper trading loop. Handles exchange connection and order execution.
    *   `features.py`: Computes real-time market features. **Crucially, it imports the strategy logic from `src/features/strategy.py`.**
*   **`features/`**: Shared business logic.
    *   `strategy.py`: **Source of Truth.** Defines the `check_mean_reversion_signal` function and constants (RSI thresholds). This single file drives both the bot and the backtests.

### `scripts/` (Backtesting & Analysis)
*   **`backtest_last_30d_live.py`**: Fetches fresh data and simulates the last 30 days. Uses `src/features/strategy.py`.
*   **`backtest_2y_comprehensive.py`**: Runs the strategy over the full 2-year dataset.
*   **`backtest_2y_live_worst.py`**: Stress test script to find historical drawdowns.
*   **`backtest_feb_1_to_5.py`**: Specialized request script.

### `data/`
*   Stores cached CSV data (e.g., `btcusdt_1m.csv`) for fast local backtesting.

### `results/`
*   Outputs from backtest scripts (reports, trade logs, and performance summaries).

## Key Design Principles
1.  **Unified Logic**: We avoid duplicating threshold numbers. `RSI_OVERSOLD` etc. are imported from `strategy.py`.
2.  **Backtest Reliability**: If it works in `backtest_last_30d_live.py`, it uses the *exact same* decision code as the live bot.
