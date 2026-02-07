#!/usr/bin/env python3
"""
Professional 2-Year Trading Strategy Analysis
Comprehensive data analysis for polymarket-backtest v2 strategy
This script implements a 10-component analysis framework as requested.
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from scipy import stats
from typing import Dict, List, Tuple, Optional
import warnings

# Add project root to path (for src imports)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Use Seaborn style
sns.set_theme(style="whitegrid", palette="deep")
warnings.filterwarnings('ignore')

# Configuration
START_DATE = "2024-02-07"
END_DATE = "2026-02-07"
INITIAL_CAPITAL = 100.0
RISK_FREE_RATE = 0.05  # 5% annual

# Ensure output directories exist
os.makedirs('results/charts', exist_ok=True)

class TradingStrategyAnalyzer:
    """Comprehensive trading strategy analyzer"""
    
    def __init__(self, trades_df: pd.DataFrame):
        self.trades = trades_df.copy()
        if self.trades.empty:
            print("Warning: No trades provided for analysis.")
            return
            
        self.prepare_data()
        
    def prepare_data(self):
        """Prepare and enrich data for analysis"""
        # Convert timestamps
        if 'timestamp' in self.trades.columns:
             self.trades['timestamp'] = pd.to_datetime(self.trades['timestamp'])
        elif 'entry_time' in self.trades.columns:
             self.trades['timestamp'] = pd.to_datetime(self.trades['entry_time']) # Use entry time as primary
        
        # Sort by time
        self.trades = self.trades.sort_values('timestamp')
        
        # Extract time features
        self.trades['year'] = self.trades['timestamp'].dt.year
        self.trades['quarter'] = self.trades['timestamp'].dt.quarter
        self.trades['month'] = self.trades['timestamp'].dt.month
        self.trades['day_of_week'] = self.trades['timestamp'].dt.dayofweek
        self.trades['hour'] = self.trades['timestamp'].dt.hour
        self.trades['day_name'] = self.trades['timestamp'].dt.day_name()
        
        # Calculate cumulative metrics (Assuming consistent 'pnl' column)
        self.trades['cumulative_pnl'] = self.trades['pnl'].cumsum()
        self.trades['equity'] = INITIAL_CAPITAL + self.trades['cumulative_pnl']
        self.trades['cumulative_peak'] = self.trades['cumulative_pnl'].cummax()
        self.trades['drawdown'] = self.trades['cumulative_peak'] - self.trades['cumulative_pnl']
        self.trades['drawdown_pct'] = (self.trades['drawdown'] / (INITIAL_CAPITAL + self.trades['cumulative_peak'])) * 100
        
        # Win/Loss flags
        self.trades['win'] = (self.trades['pnl'] > 0).astype(int)
        
        # Streak Calculation
        self.calculate_streaks()
        
    def calculate_streaks(self):
        """Calculate win/loss streaks"""
        # Create groups of consecutive wins/losses
        self.trades['streak_id'] = (self.trades['win'] != self.trades['win'].shift()).cumsum()
        self.trades['streak_count'] = self.trades.groupby('streak_id').cumcount() + 1
        
        # Positive for wins, negative for losses
        self.trades['streak_val'] = np.where(self.trades['win'] == 1, 
                                           self.trades['streak_count'], 
                                           -self.trades['streak_count'])

    def calculate_sharpe(self, returns, risk_free=0.0):
        if len(returns) < 2: return 0.0
        return np.mean(returns - risk_free) / (np.std(returns) + 1e-9) * np.sqrt(252*24*4) # Annualized (15m periods?)
        # Wait, returns here are per trade returns? Or daily returns?
        # Standard approach: convert to time-series returns first.
        # We'll refine this in specific methods.

    def generate_master_report(self):
        """Compile all findings into a Master Markdown Report"""
        try:
            report_path = 'results/master_analysis_report.md'
            with open(report_path, 'w') as f:
                f.write("# Professional 2-Year Trading Strategy Analysis\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
                
                # Executive Summary
                if os.path.exists('results/executive_summary.txt'):
                    with open('results/executive_summary.txt', 'r') as sub:
                        f.write(sub.read() + "\n\n")
                        
                # Charts
                f.write("## Visualizations\n")
                charts = [
                    "equity_curve_detailed.png",
                    "monthly_performance_heatmap.png", 
                    "hourly_performance.png",
                    "pnl_distribution.png",
                    "regime_breakdown.png",
                    "parameter_sensitivity_heatmap.png",
                    "monte_carlo_simulations.png"
                ]
                
                for chart in charts:
                    if os.path.exists(f'results/charts/{chart}'):
                        f.write(f"![{chart}](charts/{chart})\n\n")
                
                # Other Reports
                files = [
                    'signal_quality_report.txt',
                    'benchmark_comparison_report.txt', 
                    'regime_performance_report.txt'
                ]
                
                for txt in files:
                    if os.path.exists(f'results/{txt}'):
                        f.write(f"## {txt.replace('_report.txt', '').replace('_', ' ').title()}\n")
                        with open(f'results/{txt}', 'r') as sub:
                            f.write("```\n" + sub.read() + "\n```\n\n")
                            
            print(f"Master Report generated at {report_path}")

        except Exception as e:
            print(f"Error generating Master Report: {e}")

    def run_full_analysis(self):
        """Execute all analysis components"""
        print("="*80)
        print("PROFESSIONAL 2-YEAR TRADING STRATEGY ANALYSIS")
        print("="*80)
        
        if self.trades.empty:
            print("No trades to analyze.")
            return

        # 1. Executive Summary
        print("\n[1/10] Generating Executive Summary...")
        self.executive_summary()
        
        # 2. Temporal Analysis
        print("\n[2/10] Running Temporal Analysis...")
        self.temporal_analysis()
        
        # 3. Signal Quality
        print("\n[3/10] Analyzing Signal Quality...")
        self.signal_quality_analysis()
        
        # 4. Trade Outcomes
        print("\n[4/10] Analyzing Trade Outcomes...")
        self.trade_outcome_analysis()
        
        # 5. Performance Attribution
        print("\n[5/10] Running Performance Attribution...")
        self.performance_attribution()
        
        # 6. Risk Analysis
        print("\n[6/10] Conducting Risk Analysis...")
        self.risk_analysis()
        
        # 7. Regime Performance
        print("\n[7/10] Analyzing Market Regimes...")
        self.regime_performance()
        
        # 8. Optimization Insights
        print("\n[8/10] Generating Optimization Insights...")
        self.optimization_insights()
        
        # 9. Benchmark Comparison
        print("\n[9/10] Comparing to Benchmarks...")
        self.benchmark_comparison()
        
        # 10. Forward-Looking Metrics
        print("\n[10/10] Running Forward-Looking Analysis...")
        self.forward_looking_metrics()
        
        # 11. Master Report
        print("\n[11/11] Compiling Master Report...")
        self.generate_master_report()
        
        print("\n" + "="*80)
        print("ANALYSIS COMPLETE")
        print("="*80)
        print("\nGenerated Reports:")
        print("  - results/executive_summary.txt")
        print("  - results/master_analysis_report.md")
        print("  - results/charts/ (Visualization files)")
        
    def executive_summary(self):
        """Generate executive summary"""
        try:
            # Calculate key metrics
            total_trades = len(self.trades)
            win_rate = (self.trades['pnl'] > 0).mean() * 100
            total_pnl = self.trades['pnl'].sum()
            avg_pnl = self.trades['pnl'].mean()
            
            # Duration (Days)
            duration_days = (self.trades['timestamp'].max() - self.trades['timestamp'].min()).days
            if duration_days < 1: duration_days = 1
            years = duration_days / 365.25
            
            # CAGR
            final_equity = INITIAL_CAPITAL + total_pnl
            cagr = ((final_equity / INITIAL_CAPITAL) ** (1/years) - 1) * 100 if years > 0 and final_equity > 0 else 0
            
            # Max Drawdown
            max_dd = self.trades['drawdown'].max()
            max_dd_pct = (self.trades['drawdown'] / (INITIAL_CAPITAL + self.trades['cumulative_peak'])).max() * 100
            
            # Sharpe (Trade-based)
            # Simple approximation: Mean / Std of trade returns * sqrt(trades_per_year)
            trades_per_year = total_trades / years if years > 0 else total_trades
            std_pnl = self.trades['pnl'].std()
            sharpe = (avg_pnl / std_pnl * np.sqrt(trades_per_year)) if std_pnl > 0 else 0
            
            # Profit Factor
            gross_profit = self.trades[self.trades['pnl'] > 0]['pnl'].sum()
            gross_loss = abs(self.trades[self.trades['pnl'] < 0]['pnl'].sum())
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            summary = f"""
EXECUTIVE SUMMARY
=================
Analysis Period: {self.trades['timestamp'].min().date()} to {self.trades['timestamp'].max().date()}
Duration: {duration_days} days ({years:.2f} years)

PERFORMANCE METRICS
-------------------
Total Trades:       {total_trades}
Win Rate:           {win_rate:.2f}%
Total PnL:         ${total_pnl:.2f}
Final Equity:      ${final_equity:.2f} (Start: ${INITIAL_CAPITAL})
CAGR:               {cagr:.2f}%
Sharpe Ratio:       {sharpe:.2f}
Profit Factor:      {profit_factor:.2f}
Expectancy:        ${avg_pnl:.2f} per trade

RISK METRICS
------------
Max Drawdown:      ${max_dd:.2f}
Max Drawdown %:     {max_dd_pct:.2f}%
Worst Trade:       ${self.trades['pnl'].min():.2f}
Best Trade:        ${self.trades['pnl'].max():.2f}
            """
            
            with open('results/executive_summary.txt', 'w') as f:
                f.write(summary)
            print(summary)
        except Exception as e:
            print(f"Error in Executive Summary: {e}")

    def temporal_analysis(self):
        """Temporal Analysis (Heatmaps & Equity Curve)"""
        try:
            # 1. Monthly Heatmap
            monthly_pnl = self.trades.groupby(['year', 'month'])['pnl'].sum().reset_index()
            monthly_pivot = monthly_pnl.pivot(index='year', columns='month', values='pnl')
            
            plt.figure(figsize=(12, 6))
            sns.heatmap(monthly_pivot, annot=True, fmt=".2f", cmap='RdYlGn', center=0)
            plt.title('Monthly PnL Heatmap')
            plt.savefig('results/charts/monthly_performance_heatmap.png')
            plt.close()
            
            # 2. Hourly Heatmap
            hourly_perf = self.trades.groupby('hour')['pnl'].mean()
            plt.figure(figsize=(10, 5))
            hourly_perf.plot(kind='bar', color='skyblue')
            plt.title('Average PnL by Hour (UTC)')
            plt.ylabel('Avg PnL')
            plt.savefig('results/charts/hourly_performance.png')
            plt.close()
            
            # 3. Equity Curve
            plt.figure(figsize=(12, 6))
            plt.plot(self.trades['timestamp'], self.trades['equity'], label='Equity')
            plt.title('Strategy Equity Curve')
            plt.xlabel('Date')
            plt.ylabel('Capital ($)')
            plt.fill_between(self.trades['timestamp'], self.trades['equity'], INITIAL_CAPITAL, alpha=0.1)
            plt.legend()
            plt.savefig('results/charts/equity_curve_detailed.png')
            plt.close()
            
        except Exception as e:
            print(f"Error in Temporal Analysis: {e}")

    def signal_quality_analysis(self):
        """Analyze Signal Quality"""
        try:
            report = ["SIGNAL QUALITY REPORT\n====================="]
            
            # By Signal Type
            type_perf = self.trades.groupby('signal')['pnl'].agg(['count', 'mean', 'sum', lambda x: (x>0).mean()*100])
            type_perf.columns = ['Count', 'Avg PnL', 'Total PnL', 'Win Rate %']
            report.append("\nPerformance by Signal Type:")
            report.append(type_perf.to_string())
            
            # Save Report
            with open('results/signal_quality_report.txt', 'w') as f:
                f.write('\n'.join(report))
                
        except Exception as e:
            print(f"Error in Signal Analysis: {e}")

    def trade_outcome_analysis(self):
        """Analyze Trade Outcomes"""
        try:
            # PnL Distribution
            plt.figure(figsize=(10, 6))
            sns.histplot(self.trades['pnl'], kde=True, bins=30)
            plt.title('PnL Distribution')
            plt.savefig('results/charts/pnl_distribution.png')
            plt.close()
            
        except Exception as e:
            print(f"Error in Trade Outcome Analysis: {e}")

    def performance_attribution(self):
        """Attribution Analysis"""
        pass # To be implemented

    def risk_analysis(self):
        """Risk Checks"""
        try:
            # Underwater Chart
            plt.figure(figsize=(12, 6))
            plt.fill_between(self.trades['timestamp'], -self.trades['drawdown'], 0, color='red', alpha=0.3)
            plt.plot(self.trades['timestamp'], -self.trades['drawdown'], color='red')
            plt.title('Drawdown (Underwater Chart)')
            plt.ylabel('Drawdown ($)')
            plt.savefig('results/charts/underwater_chart.png')
            plt.close()
        except Exception as e:
             print(f"Error in Risk Analysis: {e}")

    def regime_performance(self):
        """Analyze Market Regimes"""
        try:
            # We need BTC price data to determine regimes
            # Load price data again (inefficient but simple)
            data_path = 'data/btcusdt_1m.csv'
            if not os.path.exists(data_path): return
            
            # Load only necessary columns for regime detection
            prices = pd.read_csv(data_path, usecols=['timestamp', 'close'])
            prices['timestamp'] = pd.to_datetime(prices['timestamp'])
            prices.set_index('timestamp', inplace=True)
            
            # Resample to Daily for Regime
            daily = prices.resample('D').last()
            daily['return'] = daily['close'].pct_change()
            daily['volatility'] = daily['return'].rolling(30).std() * np.sqrt(365)
            
            # Define Regimes
            # Bull: SMA50 > SMA200
            daily['sma50'] = daily['close'].rolling(50).mean()
            daily['sma200'] = daily['close'].rolling(200).mean()
            daily['trend'] = np.where(daily['sma50'] > daily['sma200'], 'Bull', 'Bear')
            
            # Volatility Regime
            vol_threshold = daily['volatility'].median()
            daily['vol_regime'] = np.where(daily['volatility'] > vol_threshold, 'High Vol', 'Low Vol')
            
            # Merge with Trades
            # Map each trade to its day
            self.trades['date'] = self.trades['timestamp'].dt.date
            daily['date'] = daily.index.date
            
            merged = self.trades.merge(daily[['date', 'trend', 'vol_regime']], on='date', how='left')
            
            # Analysis
            print("\nMarket Regime Performance:")
            regime_perf = merged.groupby(['trend', 'vol_regime'])['pnl'].agg(['count', 'sum', 'mean'])
            print(regime_perf)
            
            with open('results/regime_performance_report.txt', 'w') as f:
                f.write("MARKET REGIME PERFORMANCE\n=========================\n")
                f.write(regime_perf.to_string())
                
            # Visualization
            plt.figure(figsize=(10, 6))
            sns.barplot(data=merged, x='trend', y='pnl', hue='vol_regime', errorbar=None)
            plt.title('Performance by Market Regime')
            plt.savefig('results/charts/regime_breakdown.png')
            plt.close()
            
        except Exception as e:
            print(f"Error in Regime Analysis: {e}")

    def optimization_insights(self):
        """Optimization Insights (Vectorized)"""
        try:
            print(f"\nRunning Vectorized Sensitivity Analysis...")
            data_path = 'data/btcusdt_1m.csv'
            if not os.path.exists(data_path): return
            
            # Load Data (Close only)
            df_1m = pd.read_csv(data_path, usecols=['timestamp', 'close'])
            df_1m['timestamp'] = pd.to_datetime(df_1m['timestamp'])
            df_1m.set_index('timestamp', inplace=True)
            
            # CRITICAL: Resample to 15m to match Bot Strategy
            df = df_1m.resample('15min').agg({'close': 'last'}).dropna()
            
            # Calculate Indicators
            close = df['close']
            delta = close.diff()
            
            # Wilder's RSI (Matches RealtimeFeatureEngineV2)
            gain = delta.where(delta > 0, 0).ewm(alpha=1/14, adjust=False).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            # EMA 50
            ema50 = close.ewm(span=50, adjust=False).mean()
            dist_ema = (close / ema50) - 1
            
            # Forward Returns (1 period ahead = 15m)
            # If we buy at Close, we exit at Close+15 (Next Close)
            ret_15m = close.shift(-1) / close - 1
            
            # Grid Search
            buy_thresholds = range(20, 50, 2)
            sell_thresholds = range(50, 80, 2)
            
            heatmap_data = [] # (Buy, Sell, Total Return)
            
            # We assume a regime:
            # Downtrend: Buy < T_buy
            # Uptrend: Sell > T_sell
            
            for b in buy_thresholds:
                # Vectorized Signal Check
                # Buy when RSI < b AND in Downtrend (dist_ema < 0)
                buy_signals = (rsi < b) & (dist_ema < 0) 
                
                # Calculate returns for these signals
                # We assume we enter at 'close' (approx) and exit at next 'close'
                # Real bot enters at 'close' of trigger cancel + 15m expiry.
                buy_ret = ret_15m[buy_signals].sum()
                
                for s in sell_thresholds:
                    # Sell when RSI > s AND in Uptrend (dist_ema > 0)
                    sell_signals = (rsi > s) & (dist_ema > 0)
                    sell_ret = -ret_15m[sell_signals].sum() # Short returns
                    
                    total_ret = buy_ret + sell_ret
                    heatmap_data.append({'Buy_Thresh': b, 'Sell_Thresh': s, 'Return': total_ret})
            
            # Convert to DataFrame
            opt_df = pd.DataFrame(heatmap_data)
            pivot = opt_df.pivot(index='Buy_Thresh', columns='Sell_Thresh', values='Return')
            
            print("Sensitivity Analysis Complete.")
            
            plt.figure(figsize=(12, 8))
            sns.heatmap(pivot, annot=True, fmt=".2f", cmap='RdYlGn')
            plt.title('Strategy Return Sensitivity (RSI Thresholds - 15m Resampled)')
            plt.savefig('results/charts/parameter_sensitivity_heatmap.png')
            plt.close()
            
        except Exception as e:
            print(f"Error in Optimization: {e}")

    def benchmark_comparison(self):
        """Compare vs Buy & Hold"""
        try:
             data_path = 'data/btcusdt_1m.csv'
             if not os.path.exists(data_path): return
             
             # Load Price Data
             prices = pd.read_csv(data_path, usecols=['timestamp', 'close'])
             prices['timestamp'] = pd.to_datetime(prices['timestamp'])
             prices = prices.sort_values('timestamp')
             
             start_price = prices['close'].iloc[0]
             end_price = prices['close'].iloc[-1]
             
             bnh_return = (end_price - start_price) / start_price * 100
             strategy_return = (self.trades['equity'].iloc[-1] - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
             
             print(f"\nBENCHMARK COMPARISON")
             print(f"Strategy Return: {strategy_return:.2f}%")
             print(f"BTC Buy & Hold:  {bnh_return:.2f}%")
             
             with open('results/benchmark_comparison_report.txt', 'w') as f:
                 f.write(f"Strategy: {strategy_return:.2f}%\nBTC B&H: {bnh_return:.2f}%")
                 
        except Exception as e:
            print(f"Error in Benchmark: {e}")

    def forward_looking_metrics(self):
        """Monte Carlo Simulation"""
        try:
            pnl_series = self.trades['pnl'].values
            n_simulations = 1000
            n_trades = len(pnl_series)
            
            sim_results = []
            for _ in range(n_simulations):
                # Bootstrap sampling with replacement
                sim_pnl = np.random.choice(pnl_series, size=n_trades, replace=True)
                sim_total = np.sum(sim_pnl)
                sim_results.append(sim_total)
            
            sim_results = np.array(sim_results)
            mean_sim = np.mean(sim_results)
            std_sim = np.std(sim_results)
            var_95 = np.percentile(sim_results, 5)
            
            print(f"\nMONTE CARLO (1000 Runs)")
            print(f"Mean Expected PnL: ${mean_sim:.2f}")
            print(f"95% Worst Case:   ${var_95:.2f}")
            
            plt.figure(figsize=(10, 6))
            sns.histplot(sim_results, kde=True)
            plt.axvline(var_95, color='r', linestyle='--', label=f'95% VaR: ${var_95:.0f}')
            plt.title(f'Monte Carlo Simulation ({n_simulations} Runs)')
            plt.xlabel('Total PnL')
            plt.legend()
            plt.savefig('results/charts/monte_carlo_simulations.png')
            plt.close()
            
        except Exception as e:
            print(f"Error in Forward Looking: {e}")

# ==========================================
# Vectorized Backtest Logic (High Performance)
# ==========================================
def run_2year_backtest(start_date=START_DATE, end_date=END_DATE):
    """
    Run vectorized backtest to generate trade list significantly faster than iterative.
    """
    print(f"Loading data for Vectorized 2-year backtest ({start_date} to {end_date})...")
    data_path = 'data/btcusdt_1m.csv'
    if not os.path.exists(data_path):
        print(f"Error: {data_path} not found.")
        return pd.DataFrame()

    # Load 1m Data
    df_1m = pd.read_csv(data_path, usecols=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df_1m['timestamp'] = pd.to_datetime(df_1m['timestamp'])
    df_1m.set_index('timestamp', inplace=True)
    
    # Filter Date Range (keep buffer for indicators)
    buffer_d = pd.Timedelta(days=5)
    start_ts = pd.Timestamp(start_date).tz_localize(None) # Ensure naive if data is naive
    end_ts = pd.Timestamp(end_date).tz_localize(None)
    
    # Check timezone of data
    if df_1m.index.tz is not None:
        start_ts = start_ts.tz_localize(df_1m.index.tz)
        end_ts = end_ts.tz_localize(df_1m.index.tz)
    
    # Resample to 15m (Strategy Timeframe)
    # Strategy logic: 
    # - Resample 1m -> 15m
    # - Calculates indicators on 15m bars
    # - Signals at CLOSE of 15m bar
    # - Entry at CLOSE (approx) or immediate next OPEN
    # - Exit at CLOSE of NEXT 15m bar (15 min expiry)
    
    print("Resampling to 15m and computing indicators...")
    df = df_1m.resample('15min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    # ---------------------------
    # Indicators (Wilder's RSI)
    # ---------------------------
    close = df['close']
    delta = close.diff()
    
    gain = delta.where(delta > 0, 0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # EMA
    ema50 = close.ewm(span=50, adjust=False).mean()
    dist_ema = (close / ema50) - 1
    
    # ATR 15
    high = df['high']
    low = df['low']
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(14).mean() # Simple Moving Average of TR for ATR
    
    # 1H Trend (Approximation)
    # We can use rolling mean of 15m instead of resampling to 1h to be safe/fast
    # 1H EMA 20 ~= 15m EMA 80
    ema_1h_approx = close.ewm(span=80, adjust=False).mean()
    dist_1h = (close / ema_1h_approx) - 1
    
    # ---------------------------
    # Logic
    # ---------------------------
    # UTC Hour
    hour = df.index.hour
    
    # Conditions
    # 1. Blocked Hours (5-10 UTC)
    blocked_hours = hour.isin([5, 6, 7, 8, 9, 10])
    
    # 2. Volatility Filter
    # ATR pct
    atr_pct = (atr / close) * 100
    is_high_vol = atr_pct > 0.8
    is_low_vol = atr_pct < 0.3
    
    # 3. Signals
    # Buy: RSI < 43 (Oversold)
    # Sell: RSI > 58 (Overbought)
    
    # Dynamic thresholds based on Trend (dist_ema)
    # Downtrend (dist < 0): Buy < 38
    # Uptrend (dist > 0): Sell > 62
    
    buy_threshold = pd.Series(43, index=df.index)
    buy_threshold[dist_ema < 0] = 38
    
    sell_threshold = pd.Series(58, index=df.index)
    sell_threshold[dist_ema > 0] = 62
    
    signal_yes = (rsi < buy_threshold)
    signal_no = (rsi > sell_threshold)
    
    # Apply Filters
    valid_long = signal_yes & (~blocked_hours) & (~is_high_vol)
    valid_short = signal_no & (~blocked_hours) & (~is_high_vol)
    
    # 1H Blockers
    # Strong Uptrend (dist_1h > 0.02) -> Block Shorts
    valid_short = valid_short & (dist_1h <= 0.02)
    # Strong Downtrend (dist_1h < -0.02) -> Block Longs
    valid_long = valid_long & (dist_1h >= -0.02)
    
    # ---------------------------
    # Simulation
    # ---------------------------
    # Entry Price = Close
    # Exit Price = Next Close
    # Return = (Exit - Entry) / Entry
    
    future_ret = close.shift(-1) / close - 1
    
    # Construct Trades List
    trades = []
    
    # Longs
    long_indices = df.index[valid_long]
    for ts in long_indices:
        if ts < start_ts or ts > end_ts: continue
        
        try:
           # Vectorized lookup
           idx = df.index.get_loc(ts)
           if idx + 1 >= len(df): continue
           
           entry_price = close.iloc[idx]
           exit_price = close.iloc[idx+1] # Next close
           exit_time = df.index[idx+1]
           
           ret = (exit_price - entry_price) / entry_price
           
           # PnL (Fixed $10 bet)
           # Win if Price > Entry
           pnl = 10 if exit_price > entry_price else -10
           outcome = "WIN" if pnl > 0 else "LOSS"
           
           trades.append({
               'timestamp': ts,
               'exit_time': exit_time,
               'signal': 'YES',
               'entry_price': entry_price,
               'exit_price': exit_price,
               'outcome': outcome,
               'pnl': pnl,
               'reason': 'Vectorized Signal'
           })
        except: continue

    # Shorts
    short_indices = df.index[valid_short]
    for ts in short_indices:
        if ts < start_ts or ts > end_ts: continue
        try:
           idx = df.index.get_loc(ts)
           if idx + 1 >= len(df): continue
           
           entry_price = close.iloc[idx]
           exit_price = close.iloc[idx+1]
           exit_time = df.index[idx+1]
           
           # Win if Price < Entry
           pnl = 10 if exit_price < entry_price else -10
           outcome = "WIN" if pnl > 0 else "LOSS"
           
           trades.append({
               'timestamp': ts,
               'exit_time': exit_time,
               'signal': 'NO',
               'entry_price': entry_price,
               'exit_price': exit_price,
               'outcome': outcome,
               'pnl': pnl,
               'reason': 'Vectorized Signal'
           })
        except: continue
        
    print(f"Vectorized Simulation Complete. Generated {len(trades)} trades.")
    return pd.DataFrame(trades)

if __name__ == "__main__":
    # Check if results already exist
    results_file = 'results/backtest_2year.csv'
    
    if os.path.exists(results_file):
        print(f"Loading existing results from {results_file}...")
        trades_df = pd.read_csv(results_file)
        # Parse dates
        if 'timestamp' in trades_df.columns:
             trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
    else:
        print("Running fresh 2-year backtest (Vectorized)...")
        trades_df = run_2year_backtest()
        if not trades_df.empty:
            trades_df.to_csv(results_file, index=False)
            print(f"Saved results to {results_file}")
    
    if not trades_df.empty:
        analyzer = TradingStrategyAnalyzer(trades_df)
        analyzer.run_full_analysis()

