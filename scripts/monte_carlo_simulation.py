
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import sys

TRADES_FILE = "results/backtest_2y_trades.csv"

def run_monte_carlo(n_sims=10000, n_trades=500, initial_balance=100.0):
    print(f"Loading {TRADES_FILE}...")
    if not os.path.exists(TRADES_FILE):
        print("Error: Trades file not found.")
        return

    df = pd.read_csv(TRADES_FILE)
    if 'pnl' not in df.columns:
        print("Error: 'pnl' column missing in trades file.")
        return

    pnl_dist = df['pnl'].values
    print(f"Bootstrapping {n_sims} simulations of {n_trades} trades each...")
    
    final_balances = []
    max_drawdowns = []
    ruin_count = 0
    profit_count = 0
    doubling_count = 0
    
    # Vectorized bootstrap? 
    # Generating indices: (n_sims, n_trades)
    indices = np.random.randint(0, len(pnl_dist), size=(n_sims, n_trades))
    samples = pnl_dist[indices] # Shape: (n_sims, n_trades)
    
    # Cumulative Sum to get equity curves
    # Add initial balance
    # We want to check ruin during the path.
    # Cumulative PnL
    cum_pnl = np.cumsum(samples, axis=1)
    equity_curves = initial_balance + cum_pnl
    
    # Final Balances
    finals = equity_curves[:, -1]
    final_balances = finals
    
    # Ruin (Balance < 10)
    # Check if any point in path < 10
    min_equity = np.min(equity_curves, axis=1)
    ruin_count = np.sum(min_equity < 10)
    
    # Profit
    profit_count = np.sum(finals > initial_balance)
    
    # Doubling
    doubling_count = np.sum(finals > (initial_balance * 2))
    
    # Max Drawdown
    # DD = Peak - Current
    # We need running max
    # Running max along axis 1
    running_max = np.maximum.accumulate(equity_curves, axis=1)
    drawdowns = running_max - equity_curves
    # Max DD for each sim
    max_dds = np.max(drawdowns, axis=1)
    
    # Metrics
    prob_ruin = ruin_count / n_sims * 100
    prob_profit = profit_count / n_sims * 100
    prob_double = doubling_count / n_sims * 100
    
    mean_final = np.mean(finals)
    median_final = np.median(finals)
    p05 = np.percentile(finals, 5)
    p95 = np.percentile(finals, 95)
    
    mean_dd = np.mean(max_dds)
    p95_dd = np.percentile(max_dds, 95)
    
    print("\n==================================================")
    print("MONTE CARLO RISK ANALYSIS")
    print("==================================================")
    print(f"Simulations: {n_sims}")
    print(f"Trades/Sim:  {n_trades}")
    print("--------------------------------------------------")
    print(f"Prob. of Profit:   {prob_profit:.1f}%")
    print(f"Prob. of Ruin (<$10): {prob_ruin:.1f}%")
    print(f"Prob. of Doubling: {prob_double:.1f}%")
    print("--------------------------------------------------")
    print(f"Exp. Final Balance: ${mean_final:.2f}")
    print(f"Median Final Bal:   ${median_final:.2f}")
    print(f"95% CI Balance:     [${p05:.2f}, ${p95:.2f}]")
    print("--------------------------------------------------")
    print(f"Avg Max Drawdown:   ${mean_dd:.2f}")
    print(f"95% Worst DD:       ${p95_dd:.2f}")
    print("==================================================")
    
    # Visualization
    try:
        plt.figure(figsize=(15, 10))
        
        # 1. Final Balance Histogram
        plt.subplot(2, 3, 1)
        plt.hist(finals, bins=50, color='skyblue', edgecolor='black')
        plt.title('Final Balance Distribution')
        plt.xlabel('Balance ($)')
        plt.axvline(initial_balance, color='r', linestyle='--', label='Initial')
        plt.legend()
        
        # 2. Equity Curves (First 50)
        plt.subplot(2, 3, 2)
        for i in range(min(50, n_sims)):
            plt.plot(equity_curves[i], alpha=0.3)
        plt.title('Sample Equity Curves (First 50)')
        plt.xlabel('Trade #')
        plt.ylabel('Balance ($)')
        
        # 3. Max Drawdown Histogram
        plt.subplot(2, 3, 3)
        plt.hist(max_dds, bins=50, color='salmon', edgecolor='black')
        plt.title('Max Drawdown Distribution')
        plt.xlabel('Drawdown ($)')
        
        # 4. CDF
        plt.subplot(2, 3, 4)
        sorted_finals = np.sort(finals)
        yvals = np.arange(len(sorted_finals)) / float(len(sorted_finals))
        plt.plot(sorted_finals, yvals)
        plt.title('Cumulative Distribution Function (CDF)')
        plt.xlabel('Final Balance')
        plt.ylabel('Probability <= X')
        plt.grid(True)
        
        # 5. Risk vs Return (Avg Return vs Max DD - irrelevant for bootstrap?)
        # Let's show Return Distribution instead
        plt.subplot(2, 3, 5)
        returns = (finals - initial_balance) / initial_balance * 100
        plt.hist(returns, bins=50, color='lightgreen', edgecolor='black')
        plt.title('Return (%) Distribution')
        
        # 6. Heatmap or Stats text
        plt.subplot(2, 3, 6)
        plt.axis('off')
        stats_text = (
            f"Prob Profit: {prob_profit:.1f}%\n"
            f"Prob Ruin: {prob_ruin:.1f}%\n"
            f"Exp Value: ${mean_final:.2f}\n"
            f"Max DD (95%): ${p95_dd:.2f}"
        )
        plt.text(0.1, 0.5, stats_text, fontsize=12)
        plt.title('Key Risk Metrics')
        
        plt.tight_layout()
        plt.savefig("results/monte_carlo_analysis.png")
        print("Saved plot to results/monte_carlo_analysis.png")
    except Exception as e:
        print(f"Plotting failed: {e}")

if __name__ == "__main__":
    run_monte_carlo()
