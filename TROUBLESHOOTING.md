# Troubleshooting Guide

## Common Issues

### 1. `ImportError: cannot import name ... from src.features.strategy`
**Symptoms:** Running a script fails with an import error regarding the strategy module.
**Cause:** The script is being run from a directory where Python cannot see `src/`.
**Fix:**
Run scripts from the **project root**:
```bash
# CORRECT
python scripts/backtest_last_30d_live.py

# INCORRECT
cd scripts
python backtest_last_30d_live.py
```
If purely running on Windows and still seeing issues:
```powershell
$env:PYTHONPATH="f:\poly\polymarket-ml"; python scripts/backtest_last_30d_live.py
```

### 2. `RateLimitError` or "Connection refused"
**Symptoms:** Backtest script hangs or crashes while fetching data.
**Cause:** Binance API has strict rate limits.
**Fix:**
- The scripts include automatic sleeps. Wait for it to retry.
- If persistent, try treating `scripts/backtest_2y_live_worst.py` as a long-running process (can take 10+ mins).

### 3. "No Trades Found" in Backtest
**Symptoms:** Report shows 0 trades.
**Cause:**
- Data might not cover the requested date range.
- `requirements.txt` dependencies (numpy/pandas) version mismatch.
**Fix:**
- Delete `data/btcusdt_1m.csv` and re-run the fetch script to get fresh data.
- Ensure `USE_MEAN_REVERSION = True` if modifying the bot.

### 4. Live Bot Not Trading
**Symptoms:** Bot runs but places no orders.
**Cause:**
- Market conditions might not meet the strict RSI thresholds (e.g., RSI never crosses 38/62).
- API Keys missing in `.env`.
**Fix:**
- Check logs for `[DEBUG] Signal` messages.
- Verify `.env` has `PRIVATE_KEY` and `CLOB_API_KEY`.
