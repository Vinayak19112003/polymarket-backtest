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
RISK_PER_TRADE = 1.0 # Fixed risk per trade
RISK_FREE_RATE = 0.05  # 5% annual

# Ensure output directories exist
os.makedirs('results/charts', exist_ok=True)

class TradingStrategyAnalyzer:
    """Comprehensive trading strategy analyzer"""
    
    def __init__(self, trades_df: Optional[pd.DataFrame] = None):
        if trades_df is not None and not trades_df.empty:
            self.trades = trades_df.copy()
        else:
            self.trades = self.load_data()
            
        self.results_dir = "results"
        self.charts_dir = "results/charts"
        os.makedirs(self.charts_dir, exist_ok=True)
            
        if self.trades is None or self.trades.empty:
            print("Warning: No trades provided or found for analysis.")
            return
            
        self.enrich_data()
        
    def load_data(self) -> Optional[pd.DataFrame]:
        """Load trade data from multiple possible sources."""
        data_files = [
            'results/backtest_2year.csv',
            'data/backtest_trades_2year.csv',
            'results/all_trades.csv'
        ]
        
        for filepath in data_files:
            if os.path.exists(filepath):
                print(f"Loading data from: {filepath}")
                try:
                    df = pd.read_csv(filepath)
                    print(f"✅ Loaded {len(df)} trades")
                    return df
                except Exception as e:
                    print(f"Error loading {filepath}: {e}")
        
        return None

    def enrich_data(self):
        """Add all temporal and analytical features."""
        df = self.trades
        
        # Convert timestamps
        if 'timestamp' in df.columns:
             df['timestamp'] = pd.to_datetime(df['timestamp'])
        elif 'entry_time' in df.columns:
             df['timestamp'] = pd.to_datetime(df['entry_time'])
        
        # Sort by time
        df = df.sort_values('timestamp')
        
        # Temporal features
        df['year'] = df['timestamp'].dt.year
        df['quarter'] = df['timestamp'].dt.quarter
        df['month'] = df['timestamp'].dt.month
        df['month_name'] = df['timestamp'].dt.strftime('%Y-%m')
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['day_name'] = df['timestamp'].dt.day_name()
        df['hour'] = df['timestamp'].dt.hour
        df['is_weekend'] = df['day_of_week'].isin([5, 6])
        
        # Performance metrics
        df['pnl'] = pd.to_numeric(df['pnl'], errors='coerce').fillna(0)
        df['win'] = (df['pnl'] > 0).astype(int)
        df['cumulative_pnl'] = df['pnl'].cumsum()
        df['equity'] = INITIAL_CAPITAL + df['cumulative_pnl']
        df['cumulative_peak'] = df['cumulative_pnl'].cummax()
        df['drawdown'] = df['cumulative_peak'] - df['cumulative_pnl']
        df['drawdown'] = df['drawdown'].clip(lower=0) # Ensure non-negative
        
        # Rolling metrics (30 trades)
        df['rolling_winrate'] = df['win'].rolling(30, min_periods=1).mean() * 100
        df['rolling_pnl'] = df['pnl'].rolling(30, min_periods=1).sum()
        
        # Streak Calculation
        df['streak_id'] = (df['win'] != df['win'].shift()).cumsum()
        df['streak_count'] = df.groupby('streak_id').cumcount() + 1
        df['streak_val'] = np.where(df['win'] == 1, df['streak_count'], -df['streak_count'])
        
        # Trade sequence
        df['trade_num'] = range(1, len(df) + 1)
        
        self.trades = df
        
    # Alias for backward compatibility if needed
    def prepare_data(self):
        self.enrich_data()

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
        """Generate 1-page executive summary with key metrics."""
        print("\n" + "="*80)
        print("EXECUTIVE SUMMARY - 2 YEAR BACKTEST ANALYSIS")
        print("="*80)
        
        df = self.trades
        
        # Overall performance
        total_trades = len(df)
        wins = df['win'].sum()
        losses = total_trades - wins
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        total_pnl = df['pnl'].sum()
        avg_win = df[df['pnl'] > 0]['pnl'].mean()
        avg_loss = df[df['pnl'] < 0]['pnl'].mean()
        
        # Risk metrics
        max_dd = df['drawdown'].max()
        max_dd_pct = (df['drawdown'] / df['cumulative_peak']).max() * 100 if df['cumulative_peak'].max() > 0 else 0
        
        # Calculate Sharpe ratio (daily)
        daily_returns = df.groupby(df['timestamp'].dt.date)['pnl'].sum()
        sharpe = (daily_returns.mean() / daily_returns.std() * np.sqrt(365)) if daily_returns.std() > 0 else 0
        
        # Time period
        start_date = df['timestamp'].min()
        end_date = df['timestamp'].max()
        days = (end_date - start_date).days
        
        print(f"\nPERFORMANCE OVERVIEW")
        print(f"  Period: {start_date.date()} to {end_date.date()} ({days} days)")
        print(f"  Total Trades: {total_trades:,}")
        print(f"  Wins: {wins} | Losses: {losses}")
        print(f"  Win Rate: {win_rate:.2f}%")
        print(f"  Total PnL: ${total_pnl:.2f}")
        print(f"  Avg Win: ${avg_win:.3f} | Avg Loss: ${avg_loss:.3f}")
        if avg_loss != 0: # Safe division
             print(f"  Profit Factor: {abs(avg_win / avg_loss):.2f}")
        
        print(f"\nRISK METRICS")
        print(f"  Max Drawdown: ${max_dd:.2f} ({max_dd_pct:.2f}%)")
        print(f"  Sharpe Ratio: {sharpe:.2f}")
        
        # Recent performance degradation check
        recent_count = int(total_trades * 0.05)
        if recent_count > 0:
            recent_10d = df.tail(recent_count)  # Last 5% of trades
            recent_wr = (recent_10d['win'].mean() * 100)
            recent_pnl = recent_10d['pnl'].sum()
            
            print(f"\nRECENT PERFORMANCE (Last {len(recent_10d)} trades)")
            print(f"  Win Rate: {recent_wr:.2f}%")
            print(f"  PnL: ${recent_pnl:.2f}")
            
            if recent_wr < win_rate - 5:
                print(f"\n⚠️ WARNING: Recent performance DOWN {win_rate - recent_wr:.1f}% from overall!")
                print("  → Investigate recent market regime changes")
                print("  → Consider parameter adjustment or temporary pause")
        else:
            recent_wr = win_rate
            
        # Save to file
        with open(f"{self.results_dir}/executive_summary.txt", 'w') as f:
            f.write("="*80 + "\n")
            f.write("EXECUTIVE SUMMARY\n")
            f.write("="*80 + "\n\n")
            f.write(f"Win Rate: {win_rate:.2f}%\n")
            f.write(f"Total PnL: ${total_pnl:.2f}\n")
            f.write(f"Sharpe Ratio: {sharpe:.2f}\n")
            f.write(f"Max Drawdown: ${max_dd:.2f}\n")
            f.write(f"Recent Win Rate: {recent_wr:.2f}%\n")
        
        print(f"\n✅ Saved: {self.results_dir}/executive_summary.txt")

    def temporal_analysis(self):
        """Deep dive into time-based performance patterns."""
        print("\n" + "="*80)
        print("TEMPORAL PERFORMANCE ANALYSIS")
        print("="*80)
        
        df = self.trades
        
        # === HOURLY ANALYSIS ===
        print("\n### HOURLY BREAKDOWN (0-23 UTC) ###")
        hourly = df.groupby('hour').agg({
            'pnl': ['sum', 'mean', 'count'],
            'win': 'mean'
        })
        hourly.columns = ['Total_PnL', 'Avg_PnL', 'Trades', 'Win_Rate']
        hourly['Win_Rate'] = hourly['Win_Rate'] * 100
        hourly = hourly.round(2)
        
        # Sort by total PnL
        hourly_sorted = hourly.sort_values('Total_PnL', ascending=False)
        best_3_hours = hourly_sorted.head(3)
        worst_3_hours = hourly_sorted.tail(3)
        
        print(f"\n🎯 TOP 3 BEST HOURS:")
        for idx, row in best_3_hours.iterrows():
            print(f"   Hour {idx:02d}: ${row['Total_PnL']:.2f} PnL, "
                  f"{row['Win_Rate']:.1f}% WR, {int(row['Trades'])} trades")
        
        print(f"\n❌ TOP 3 WORST HOURS:")
        for idx, row in worst_3_hours.iterrows():
            print(f"   Hour {idx:02d}: ${row['Total_PnL']:.2f} PnL, "
                  f"{row['Win_Rate']:.1f}% WR, {int(row['Trades'])} trades")
        
        potential_gain = abs(worst_3_hours[worst_3_hours['Total_PnL'] < 0]['Total_PnL'].sum())
        print(f"\n💡 RECOMMENDATION: Avoid hours {worst_3_hours.index.tolist()}")
        print(f"   This would save ${potential_gain:.2f} in losses")
        
        # === DAY OF WEEK ANALYSIS ===
        print("\n### DAY OF WEEK BREAKDOWN ###")
        dow_agg = df.groupby('day_name').agg({
            'pnl': ['sum', 'mean'],
            'win': 'mean',
            'trade_num': 'count'
        })
        dow_agg.columns = ['Total_PnL', 'Avg_PnL', 'Win_Rate', 'Trades']
        dow_agg['Win_Rate'] = dow_agg['Win_Rate'] * 100
        # Reindex for proper ordering
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        dow_agg = dow_agg.reindex(days_order).dropna()
        dow_agg = dow_agg.round(2)
        
        print(dow_agg.to_string())
        
        best_day = dow_agg['Total_PnL'].idxmax()
        worst_day = dow_agg['Total_PnL'].idxmin()
        print(f"\n   Best day: {best_day} (${dow_agg.loc[best_day, 'Total_PnL']:.2f})")
        print(f"   Worst day: {worst_day} (${dow_agg.loc[worst_day, 'Total_PnL']:.2f})")
        
        # === MONTHLY TRENDS ===
        print("\n### MONTHLY PERFORMANCE ###")
        monthly = df.groupby('month_name').agg({
            'pnl': ['sum', 'mean'],
            'win': 'mean',
            'trade_num': 'count'
        })
        monthly.columns = ['Total_PnL', 'Avg_PnL', 'Win_Rate', 'Trades']
        monthly['Win_Rate'] = monthly['Win_Rate'] * 100
        monthly = monthly.round(2)
        
        print(monthly.to_string())
        
        # Performance degradation check
        if len(monthly) > 6:
            first_6m = monthly.head(6)['Win_Rate'].mean()
            last_6m = monthly.tail(6)['Win_Rate'].mean()
            
            print(f"\n📊 TREND ANALYSIS:")
            print(f"   First 6 months avg WR: {first_6m:.2f}%")
            print(f"   Last 6 months avg WR: {last_6m:.2f}%")
            print(f"   Change: {last_6m - first_6m:+.2f}%")
            
            if last_6m < first_6m - 3:
                print(f"\n⚠️ ALERT: Performance degrading over time!")
                print("   Possible causes:")
                print("   1. Market regime changed (trending → ranging or vice versa)")
                print("   2. Optimal parameters shifted")
                print("   → Consider reoptimization")
        
        # Save detailed report
        with open(f"{self.results_dir}/temporal_analysis.txt", 'w') as f:
            f.write("TEMPORAL PERFORMANCE ANALYSIS\n")
            f.write("="*80 + "\n\n")
            f.write(hourly.to_string() + "\n\n")
            f.write(dow_agg.to_string() + "\n\n")
            f.write(monthly.to_string())

        # Generate Visualizations
        self.plot_temporal_heatmaps(df)

    def plot_temporal_heatmaps(self, df):
        """Generate charts for temporal analysis"""
        try:
            # 1. Monthly Heatmap
            monthly_pnl = df.groupby(['year', 'month'])['pnl'].sum().reset_index()
            monthly_pivot = monthly_pnl.pivot(index='year', columns='month', values='pnl')
            
            plt.figure(figsize=(12, 6))
            sns.heatmap(monthly_pivot, annot=True, fmt=".2f", cmap='RdYlGn', center=0)
            plt.title('Monthly PnL Heatmap')
            plt.savefig(f'{self.charts_dir}/monthly_performance_heatmap.png')
            plt.close()
            
            # 2. Hourly Heatmap
            hourly_perf = df.groupby('hour')['pnl'].mean()
            plt.figure(figsize=(10, 5))
            hourly_perf.plot(kind='bar', color='skyblue')
            plt.title('Average PnL by Hour (UTC)')
            plt.ylabel('Avg PnL')
            plt.savefig(f'{self.charts_dir}/hourly_performance.png')
            plt.close()
            
            # 3. Equity Curve
            plt.figure(figsize=(12, 6))
            plt.plot(df['timestamp'], df['equity'], label='Equity')
            plt.title('Strategy Equity Curve')
            plt.xlabel('Date')
            plt.ylabel('Capital ($)')
            plt.fill_between(df['timestamp'], df['equity'], INITIAL_CAPITAL, alpha=0.1)
            plt.legend()
            plt.savefig(f'{self.charts_dir}/equity_curve_detailed.png')
            plt.close()
        except Exception as e:
            print(f"Error plotting temporal charts: {e}")

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
            with open(f"{self.results_dir}/signal_quality_report.txt", 'w') as f:
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
            plt.savefig(f'{self.charts_dir}/pnl_distribution.png')
            plt.close()
            
        except Exception as e:
             print(f"Error in Trade Outcome Analysis: {e}")

    def performance_attribution(self):
        """Attribution Analysis by Signal and Streak"""
        print("\n" + "="*80)
        print("PERFORMANCE ATTRIBUTION")
        print("="*80)
        
        df = self.trades
        
        # 1. By Signal Type
        print("\n### BY SIGNAL TYPE ###")
        sig_perf = df.groupby('signal')['pnl'].agg(['count', 'sum', 'mean', lambda x: (x>0).mean()*100])
        sig_perf.columns = ['Trades', 'Total PnL', 'Avg PnL', 'Win Rate %']
        print(sig_perf)
        
        # 2. By Streak Context (After Win vs After Loss)
        print("\n### BY STREAK CONTEXT ###")
        # Shift win to see previous outcome
        df['prev_win'] = df['win'].shift()
        streak_perf = df.groupby('prev_win')['pnl'].agg(['count', 'sum', 'mean', lambda x: (x>0).mean()*100])
        streak_perf.index = ['After Loss', 'After Win']
        streak_perf.columns = ['Trades', 'Total PnL', 'Avg PnL', 'Win Rate %']
        print(streak_perf)
        
        # 3. By Volatility (if ATR available)
        if 'atr' in df.columns and 'close' in df.columns:
            df['atr_pct'] = (df['atr'] / df['close']) * 100
            df['vol_bin'] = pd.qcut(df['atr_pct'], q=5, labels=['Very Low', 'Low', 'Med', 'High', 'Very High'])
            
            print("\n### BY VOLATILITY REGIME (ATR %) ###")
            vol_perf = df.groupby('vol_bin')['pnl'].agg(['count', 'sum', 'mean', lambda x: (x>0).mean()*100])
            vol_perf.columns = ['Trades', 'Total PnL', 'Avg PnL', 'Win Rate %']
            print(vol_perf)
            
        # 4. By RSI Bin (if available)
        if 'rsi' in df.columns:
            df['rsi_bin'] = pd.cut(df['rsi'], bins=[0, 30, 40, 50, 60, 70, 100], labels=['<30', '30-40', '40-50', '50-60', '60-70', '>70'])
            print("\n### BY RSI ZONE ###")
            rsi_perf = df.groupby('rsi_bin')['pnl'].agg(['count', 'sum', 'mean', lambda x: (x>0).mean()*100])
            rsi_perf.columns = ['Trades', 'Total PnL', 'Avg PnL', 'Win Rate %']
            print(rsi_perf)

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
    # ---------------------------
    # Logic (Standardized V2 - Leak Free)
    # ---------------------------
    # UTC Hour
    hour = df.index.hour
    
    # Shift Indicators for Signal Generation (T-1)
    prev_rsi = rsi.shift(1)
    prev_close = close.shift(1)
    prev_ema = ema.shift(1)
    prev_dist_ema = (prev_close / prev_ema) - 1
    
    # 1H Trend (Shifted/Aligned)
    # We already have dist_1h (approximated). Ideally should be shifted too.
    # dist_1h was calculated on 'close'. 
    prev_dist_1h = dist_1h.shift(1)
    
    # Conditions
    # 1. Blocked Hours (5-10 UTC + 15-16 UTC)
    # Note: Analysis script had 5,6,7,8,9,10. We should match new strategy: 5-9 & 15-16.
    # Hour 10 is now UNBLOCKED in live bot? Let's verify.
    # Live bot: BLOCKED_HOURS = [5, 6, 7, 8, 9, 15, 16]
    blocked_hours = hour.isin([5, 6, 7, 8, 9, 15, 16])
    
    # 2. Volatility Filter
    # ATR pct (Computed on T-1 to decide for T? Or T's Open?)
    # Live Logic: uses current ATR (rolling) at moment of signal.
    # Safest is T-1 ATR.
    prev_atr = atr.shift(1)
    atr_pct = (prev_atr / prev_close) * 100
    is_high_vol = atr_pct > 0.8
    
    # 3. Signals (Using T-1)
    # Buy: RSI < 43 (Oversold) -> 38/62 aligned
    # Sell: RSI > 58 (Overbought)
    
    buy_threshold = pd.Series(38, index=df.index) # Aligned Default
    buy_threshold[prev_dist_ema < 0] = 35         # Downtrend
    
    sell_threshold = pd.Series(62, index=df.index) # Aligned Default
    sell_threshold[prev_dist_ema > 0] = 65         # Uptrend
    
    signal_yes = (prev_rsi < buy_threshold)
    signal_no = (prev_rsi > sell_threshold)
    
    # Apply Filters
    valid_long = signal_yes & (~blocked_hours) & (~is_high_vol)
    valid_short = signal_no & (~blocked_hours) & (~is_high_vol)
    
    # 1H Blockers (Using T-1)
    valid_short = valid_short & (prev_dist_1h <= 0.02)
    valid_long = valid_long & (prev_dist_1h >= -0.02)
    
    # ---------------------------
    # Simulation
    # ---------------------------
    # Entry: Open of T (Current Candle)
    # Exit: Close of T (Current Candle) - Day Trade / Scalp
    # Live Bot: Signal at T (Close of T-1). Entry at Open of T. Exit at Close of T+15m (which is T).
    
    # Return = (Close - Open) / Open
    # Note: Previous logic was Entry=Close(T), Exit=Close(T+1). That is "Next Bar" trade.
    # "Standard" Logic: Entry=Open(T), Exit=Close(T).
    
    future_ret = (close - open_price) / open_price
    
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
           
           # PnL (Fixed Risk)
           # Win if Price > Entry
           pnl = RISK_PER_TRADE if exit_price > entry_price else -RISK_PER_TRADE
           outcome = "WIN" if pnl > 0 else "LOSS"
           
           trades.append({
               'timestamp': ts,
               'exit_time': exit_time,
               'signal': 'YES',
               'entry_price': entry_price,
               'exit_price': exit_price,
               'outcome': outcome,
               'pnl': pnl,
               'reason': 'Vectorized Signal',
               'rsi': rsi.iloc[idx],
               'atr': atr.iloc[idx],
               'close': entry_price
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
           pnl = RISK_PER_TRADE if exit_price < entry_price else -RISK_PER_TRADE
           outcome = "WIN" if pnl > 0 else "LOSS"
           
           trades.append({
               'timestamp': ts,
               'exit_time': exit_time,
               'signal': 'NO',
               'entry_price': entry_price,
               'exit_price': exit_price,
               'outcome': outcome,
               'pnl': pnl,
               'reason': 'Vectorized Signal',
               'rsi': rsi.iloc[idx],
               'atr': atr.iloc[idx],
               'close': entry_price
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

