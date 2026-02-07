# Deprecated Scripts

⚠️ **WARNING: DO NOT USE THESE SCRIPTS**

These scripts are kept for historical reference only. They contain issues that make them unsuitable for production use.

## backtest_2y.py
**Issue:** Forward bias / look-ahead in V1 strategy
**Performance After Fix:** 50.79% WR, -133% ROI (unprofitable)
**Replacement:** Use `scripts/backtest/backtest_enhanced_v2.py`

## run_recent.py
**Issue:** Same-bar look-ahead bias
**Replacement:** Use `scripts/backtest/backtest_last_30d_live.py`

## verify_fixed.py
**Purpose:** One-off integrity verification after audit
**Status:** Served its purpose, no longer needed

## verify_aligned_strategy.py
**Purpose:** One-off alignment verification
**Status:** Use `backtest_enhanced_v2.py` for ongoing validation

***

For details, see [BACKTEST_INTEGRITY_REPORT.md](../../BACKTEST_INTEGRITY_REPORT.md)
