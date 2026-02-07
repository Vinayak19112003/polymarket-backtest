# Polymarket Trading Bot V2 (Enhanced)

⚠️ **IMPORTANT: This is V2 Enhanced - DO NOT mix with V1 (archived)**

## 🚀 Quick Start (V2 Production)

### Paper Trading (Recommended First Step)
```bash
python scripts/trading/dry_run.py
```

### Live Trading (After Paper Trading Success)
```bash
python src/bot/main.py
```

### Backtesting V2
```bash
python scripts/backtest/backtest_enhanced_v2.py
```

## 📂 Repository Structure

```
polymarket-backtest/
├── src/
│   ├── bot/           # Live trading bot
│   ├── features/      # Strategy logic (unified)
│   └── ...
├── scripts/
│   ├── backtest/      # Production backtest scripts
│   │   ├── utils/     # Helper utilities
│   │   └── README.md  # Backtest documentation
│   └── trading/       # Live/paper trading
├── results/           # Backtest outputs
├── archive/
│   ├── deprecated/    # Invalid/old scripts
│   └── v1_baseline/   # Historical baseline
├── BACKTEST_INTEGRITY_REPORT.md  # Audit results
└── README.md
```

See [scripts/backtest/README.md](scripts/backtest/README.md) for detailed backtest documentation.

## 📊 V2 Performance (Validated)
- **Win Rate:** 58.01%
- **ROI (2Y):** 777% (non-compounding)
- **With 1% Slippage:** $637 PnL (ROBUST)
- **Risk of Ruin:** 0.0%
- **Stability (CV):** 0.79 (Excellent)

## Strategy Parameters (Production v2.1.0)
- **RSI Oversold**: 38 (Buy YES when RSI < 38)
- **RSI Overbought**: 62 (Buy NO when RSI > 62)
- **Blocked Hours**: 5-9 UTC, 15-16 UTC (Low liquidity / unprofitable)
- **Premium Hours**: 20-23 UTC (Highest win rates)
- **Entry Price**: Dynamic (Mean Reversion)
- **Risk Per Trade**: 1% (non-compounding)

## ⚠️ Version Warnings
- ❌ DO NOT use files from `archive/v1_baseline/`
- ❌ DO NOT mix V1 and V2 strategy logic
- ✅ ONLY use `src/features/strategy.py` for trading decisions
- ✅ ONLY use `scripts/backtest/backtest_enhanced_v2.py` for V2 validation

## 🗺️ Roadmap
- [x] V1 Baseline strategy (Archived)
- [x] V2 Enhanced with filters
- [x] Comprehensive backtesting
- [x] Slippage sensitivity validation
- [ ] Paper trading (7 days) ← **YOU ARE HERE**
- [ ] Live trading ($50-100)
- [ ] Scale to full capital

---
**Current Version:** V2 Enhanced (Production Ready)
**Status:** Cleared for Paper Trading
**Last Validation:** 2026-02-06
