# Backtest Scripts

## 📊 Production Scripts

### Primary Benchmark (Always Run First)

#### `backtest_enhanced_v2.py` ⭐ **PRIMARY SOURCE OF TRUTH**
Official V2 strategy backtest over 2-year history.

**Features:**
- RSI mean reversion (38/62 base, 35/65 dynamic)
- Volatility filter (blocks ATR > 0.8%)
- Multi-timeframe (1H trend confirmation)
- Time-of-day filter (blocks low-liquidity hours)

**Performance:** 58.54% WR, +$504.36 PnL (504% ROI on $1 risk)

**Usage:**
```bash
python scripts/backtest/backtest_enhanced_v2.py
```

**Output:** `results/backtest_enhanced_v2_trades.csv`

***

### Recent Validation (Short-term Verification)

#### `backtest_last_30d_live.py`
30-day rolling validation matching live bot logic.

**Usage:**
```bash
python scripts/backtest/backtest_last_30d_live.py
```

**Output:** `results/backtest_30d_report.txt`

#### `backtest_last_week_exact.py`
7-day exact validation simulating live feed.

**Usage:**
```bash
python scripts/backtest/backtest_last_week_exact.py
```

#### `backtest_last_24h_exact.py`
24-hour quick validation.

**Usage:**
```bash
python scripts/backtest/backtest_last_24h_exact.py
```

#### `backtest_feb_1_to_5.py`
Specific period validation (Feb 1-5, 2026).

**Usage:**
```bash
python scripts/backtest/backtest_feb_1_to_5.py
```

***

### Execution Analysis

#### `backtest_with_orderbook.py`
Realistic execution simulation with orderbook depth.

**Features:**
- Simulates bid/ask spread
- Fill probability based on liquidity
- Post-signal orderbook snapshots

**Usage:**
```bash
python scripts/backtest/backtest_with_orderbook.py
```

#### `slippage_test.py`
Tests multiple slippage scenarios.

**Scenarios:**
- Entry prices: 0.48, 0.50, 0.52
- Slippage: 0%, 1%, 2%

**Usage:**
```bash
python scripts/backtest/slippage_test.py
```

***

### Validation Tools

#### `walk_forward_validation.py`
Walk-forward optimization validation to avoid overfitting.

**Features:**
- Rolling train/test splits
- Out-of-sample performance
- Parameter stability check

**Usage:**
```bash
python scripts/backtest/walk_forward_validation.py
```

#### `monte_carlo_simulation.py`
Monte Carlo bootstrap for risk assessment.

**Features:**
- 10,000 simulations
- Confidence intervals
- Maximum drawdown distribution

**Usage:**
```bash
python scripts/backtest/monte_carlo_simulation.py
```

**Output:** `results/monte_carlo_report.txt`

***

## 🛠️ Utility Scripts

Located in `scripts/backtest/utils/`:

- **calc_drawdown.py** - Calculate max drawdown from trade CSV
- **calc_streaks.py** - Calculate win/loss streaks
- **check_data.py** - Verify data quality and completeness
- **check_entry_pricing.py** - Analyze entry price distribution

**Usage Example:**
```bash
python scripts/backtest/utils/calc_drawdown.py results/backtest_enhanced_v2_trades.csv
```

***

## 🗄️ Deprecated Scripts

Located in `archive/deprecated/`:

- **backtest_2y.py** - V1 strategy (forward bias, unprofitable after fix)
- **run_recent.py** - Had look-ahead bias (use backtest_last_30d_live.py instead)
- **verify_fixed.py** - One-off integrity verification
- **verify_aligned_strategy.py** - One-off alignment verification

⚠️ **DO NOT USE** these scripts. They are kept for historical reference only.

***

## 📋 Recommended Workflow

### Daily Validation
```bash
# Quick 24h check
python scripts/backtest/backtest_last_24h_exact.py
```

### Weekly Validation
```bash
# 7-day validation
python scripts/backtest/backtest_last_week_exact.py

# 30-day validation
python scripts/backtest/backtest_last_30d_live.py
```

### Full Re-validation (After Strategy Changes)
```bash
# Primary benchmark (2-year)
python scripts/backtest/backtest_enhanced_v2.py

# Slippage scenarios
python scripts/backtest/slippage_test.py

# Walk-forward validation
python scripts/backtest/walk_forward_validation.py

# Monte Carlo risk assessment
python scripts/backtest/monte_carlo_simulation.py
```

***

## 🎯 Key Metrics

All scripts should target:
- **Win Rate:** ≥ 56%
- **Trade Count:** 30-50/day (after filters)
- **ROI:** Positive over any 30-day period
- **Max Drawdown:** < 20%

***

## 🔍 Backtest Integrity

All production scripts verified by `BACKTEST_INTEGRITY_REPORT.md`:
- ✅ No forward/look-ahead bias
- ✅ Uses shifted indicators (prev_rsi, prev_close)
- ✅ Realistic entry/exit timing
- ✅ Matches live bot logic

Last audited: 2026-02-07
