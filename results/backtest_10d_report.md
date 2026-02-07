# 10-Day Backtest Report (V2 Strategy)

**Period:** 2026-01-28 to 2026-02-07
**Strategy:** Dynamic RSI V2 (Mean Reversion)
**Data:** 1-minute BTC/USDT (Binance)

## Summary Metrics
- **Total Trades:** 87
- **Win Rate:** 48.28% (42 Wins / 45 Losses)
- **Net PnL:** -$30.00 (Assuming constant $10 size/risk)
- **Expectation:** Strategy aims for 58%, currently underperforming in this specific 10-day window.

## Breakdown by Signal Type
| Signal | Trades | Wins | Losses | Win Rate |
| :--- | :--- | :--- | :--- | :--- |
| **NO (Short)** | 37 | 20 | 17 | **54.05%** |
| **YES (Long)** | 50 | 22 | 28 | 44.00% |

## Analysis
- **Shorts (Mean Reversion Down)** performed significantly better (54%) than Longs.
- **Longs (Mean Reversion Up)** dragged down the overall performance.
- **Context:** If BTC was in a strong trend during these 10 days, mean reversion strategies can suffer. The strategy *does* have trend filters, but the "YES" performance suggests buying dips in this specific regime was risky.

## Signal Log
See `results/backtest_10d.csv` for trade-by-trade details.
