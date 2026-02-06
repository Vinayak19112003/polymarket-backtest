
"""
Database Infrastructure Layer
- Manages connection to SQLite (default)
- Abstraction for future Postgres migration
- Stores Trades and Logs
"""
import sqlite3
import json
import os
from datetime import datetime

DB_FILE = "data/polymarket_bot.db"

def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Trades Table
    c.execute('''
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        signal TEXT,
        entry_price REAL,
        exit_price REAL,
        result TEXT,
        pnl REAL,
        metadata TEXT
    )
    ''')
    
    # Audit Logs Table
    c.execute('''
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        event_type TEXT,
        message TEXT,
        level TEXT
    )
    ''')
    
    conn.commit()
    conn.close()
    print(f"[DB] Initialized {DB_FILE}")

class TradeDatabase:
    def __init__(self, db_path=DB_FILE):
        self.db_path = db_path
        
    def log_trade(self, trade_dict):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        entry = (
            str(trade_dict.get('timestamp', datetime.now())),
            trade_dict.get('signal'),
            trade_dict.get('entry_price'),
            trade_dict.get('exit_price'),
            trade_dict.get('result'),
            trade_dict.get('pnl'),
            json.dumps(trade_dict, default=str) # Dump full dict as metadata
        )
        
        c.execute('''
        INSERT INTO trades (timestamp, signal, entry_price, exit_price, result, pnl, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', entry)
        
        conn.commit()
        conn.close()
        # print(f"[DB] Saved trade {trade_dict.get('signal')}")

    def get_recent_trades(self, limit=50):
        # Useful for Dashboard
        conn = sqlite3.connect(self.db_path)
        # Return as dicts?
        df = pd.read_sql_query(f"SELECT * FROM trades ORDER BY id DESC LIMIT {limit}", conn)
        conn.close()
        return df

if __name__ == "__main__":
    init_db()
    
    # Test
    db = TradeDatabase()
    db.log_trade({
        'timestamp': datetime.now(),
        'signal': 'TEST',
        'entry_price': 0.5,
        'exit_price': 0.6,
        'result': 'WIN',
        'pnl': 0.18
    })
    print("Test trade saved.")
