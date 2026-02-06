
"""
Monthly Performance Report Generator
- Calculates Monthly ROI, Win Rate, Drawdown
- Generates a text-based report (PDF generation requires non-standard libs like FPDF, minimizing deps for now)
- Saves to results/monthly_report_YYYY_MM.txt
"""
import pandas as pd
import os
import sys
from datetime import datetime

def generate_monthly_report():
    print("Generating Monthly Report...")
    
    # Load data
    trades_path = "results/backtest_enhanced_v2_trades.csv"
    if not os.path.exists(trades_path):
        print(f"Error: {trades_path} not found.")
        return
        
    df = pd.read_csv(trades_path, parse_dates=['timestamp'])
    
    # Filter for current month (or last available month in data)
    last_date = df['timestamp'].max()
    target_month = last_date.strftime("%Y-%m")
    
    print(f"Target Month: {target_month}")
    
    df_month = df[df['timestamp'].dt.strftime("%Y-%m") == target_month]
    
    if df_month.empty:
        print("No trades for this month.")
        return
        
    # Metrics
    total_trades = len(df_month)
    wins = len(df_month[df_month['result'] == 'WIN'])
    win_rate = wins / total_trades * 100
    pnl = df_month['pnl'].sum()
    
    # Drawdown
    df_month = df_month.sort_values('timestamp')
    df_month['equity'] = df_month['pnl'].cumsum()
    peak = df_month['equity'].cummax()
    dd = peak - df_month['equity']
    max_dd = dd.max()
    
    report_content = f"""
==================================================
MONTHLY TRADING REPORT: {target_month}
==================================================
Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

SUMMARY
--------------------------------------------------
Total Trades:      {total_trades}
Win Rate:          {win_rate:.2f}%
Net PnL (Units):   ${pnl:.2f}
Max Drawdown:      ${max_dd:.2f}

STRATEGY PERFORMANCE
--------------------------------------------------
Best Day:  {df_month.loc[df_month['pnl'].idxmax()]['timestamp']} (${df_month['pnl'].max():.2f})
Worst Day: {df_month.loc[df_month['pnl'].idxmin()]['timestamp']} (${df_month['pnl'].min():.2f})

VOLATILITY & FILTERS
--------------------------------------------------
(See Dashboard for Filter Rejections)

RECOMMENDATIONS
--------------------------------------------------
- If Win Rate < 55%: Review blocked trades in Dashboard.
- If Max DD > 15%: Investigate volatility regime filter.

==================================================
"""
    
    # Save
    filename = f"results/monthly_report_{target_month}.txt"
    with open(filename, "w") as f:
        f.write(report_content)
        
    print(report_content)
    print(f"Saved report to {filename}")

if __name__ == "__main__":
    generate_monthly_report()
