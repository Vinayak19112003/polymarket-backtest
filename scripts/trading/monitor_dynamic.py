#!/usr/bin/env python3
"""Monitor dynamic paper trading."""
import time
import os
from datetime import datetime

def tail_log(log_path, lines=20):
    """Show last N lines of log."""
    if not os.path.exists(log_path):
        return []
    
    with open(log_path, 'r') as f:
        return f.readlines()[-lines:]

def main():
    log_dir = 'logs/paper_trading'
    
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("=" * 80)
        print(f"DYNAMIC PAPER TRADING MONITOR - {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 80)
        
        # Find latest log
        if os.path.exists(log_dir):
            logs = sorted([f for f in os.listdir(log_dir) if f.startswith('dynamic_session')])
            
            if logs:
                latest = os.path.join(log_dir, logs[-1])
                lines = tail_log(latest, 25)
                
                print("\nLATEST ACTIVITY:")
                print("-" * 80)
                for line in lines:
                    print(line.rstrip())
            else:
                print("\nNo log files found")
        else:
            print("\nLog directory not found")
        
        print("\n" + "=" * 80)
        print("Press Ctrl+C to exit")
        
        time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped")
