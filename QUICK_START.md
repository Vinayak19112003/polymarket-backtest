# Quick Start Guide - V2 Enhanced Strategy

## 🎯 What to Run (V2 Only)

### For Backtesting
```bash
# Main V2 backtest
python scripts/backtest/backtest_enhanced_v2.py

# Slippage sensitivity
python scripts/backtest/slippage_test.py

# Risk analysis
python scripts/backtest/monte_carlo_simulation.py
```

### For Paper Trading
```bash
# Start paper trading (NO REAL MONEY)
python scripts/trading/dry_run.py

# Monitor with dashboard
python -m streamlit run scripts/trading/dashboard.py
```

### For Live Trading
```bash
# ONLY AFTER SUCCESSFUL PAPER TRADING
python src/bot/main.py
```

## ⚠️ What NOT to Run

❌ `archive/v1_baseline/*` - OLD VERSION, DO NOT USE
❌ `scripts/backtest_2y_comprehensive.py` - Moved to archive
❌ Any script in archive/ folder

## 📂 Where to Find Things

| What | Where |
|------|-------|
| Strategy Logic | `src/features/strategy.py` |
| Live Trading | `src/bot/main.py` |
| Paper Trading | `scripts/trading/dry_run.py` |
| V2 Backtest | `scripts/backtest/backtest_enhanced_v2.py` |
| Results | `results/v2_production/` |
| Old V1 Code | `archive/v1_baseline/` (reference only) |

## 🚀 Current Status
**Version:** V2 Enhanced (Production)
**Validation:** ✅ Complete (9/9 pass)
**Next Step:** Paper Trading (7 days)
**Ready for:** Paper Trading → Live ($50-100)
