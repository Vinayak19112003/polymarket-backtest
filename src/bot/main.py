"""
Real Polymarket Paper Trader - DEMO Balance, REAL Prices
Uses real Polymarket orderbook from CLOB API with paper trading.

Integrates:
- resolve_btc15m_market.py for market discovery
- clob_orderbook_poll.py for real orderbook
- ML model for probability prediction
- Realistic limit order simulation
- 15-minute settlement
"""
import sys
import os
import time
import math
import json
import csv
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional, List
from enum import Enum

# Import components
from .market import resolve_market, get_market_result
from .orderbook import CLOBOrderbookPoller
from .price_feed import BinancePriceFeed
from .features import RealtimeFeatureEngine as FeatureEngine
from . import config
from . import telegram_notifier as tg


# Configuration
DEMO_BALANCE = config.DEMO_START_BALANCE
RISK_PER_TRADE = config.RISK_PER_TRADE
EDGE_THRESHOLD = 0.0  # Removed - trade immediately when signal locks
FEE_RATE = config.FEE_RATE
FILL_TIMEOUT_SECONDS = config.ORDER_TIMEOUT_SECONDS
SETTLEMENT_MINUTES = 15

# Output files
TRADES_FILE = "logs/trades.csv"
EQUITY_FILE = "logs/equity.csv"


class OrderSide(Enum):
    YES = "YES"
    NO = "NO"


@dataclass
class DemoOrder:
    """Demo limit order."""
    order_id: str
    timestamp: datetime
    side: OrderSide
    limit_price: float
    bet_amount: float  # Total cost = shares * price
    shares: int  # Number of shares
    p_up: float
    yes_bid: float
    yes_ask: float
    no_bid: float
    no_ask: float
    yes_token_id: Optional[str] = None
    no_token_id: Optional[str] = None
    settlement_result: Optional[str] = None
    price_to_beat: float = 0.0  # BTC at market open (for settlement)
    filled: bool = False
    fill_price: float = 0.0
    fill_time: Optional[datetime] = None
    cancelled: bool = False
    settled: bool = False
    settlement_time: Optional[datetime] = None
    btc_at_entry: float = 0.0
    btc_at_settle: float = 0.0
    pnl: float = 0.0
    fees: float = 0.0


class RealPolymarketPaperTrader:
    """Paper trader using real Polymarket orderbook data."""
    
    def __init__(self):
        # Components
        self.orderbook_poller = CLOBOrderbookPoller()
        self.price_feed = BinancePriceFeed(symbol='BTCUSDT')
        # Removed duplicate callback registration (Done in start())
        self.feature_engine = FeatureEngine()
        
        # State
        self.balance = self._load_last_balance()
        self.peak_balance = self.balance
        self.orders: List[DemoOrder] = []
        self.pending_order: Optional[DemoOrder] = None
        self.open_position: Optional[DemoOrder] = None
        self.order_counter = 0
        self.empty_ticks = 0 # Watchdog counter
        
        self.running = False
        self.market_slug: Optional[str] = None
        self.price_to_beat: float = 0.0  # BTC price at market open
        
        # Ensure logs directory exists
        os.makedirs("logs", exist_ok=True)
        
        # Dashboard Data
        self.last_prob: float = 0.0
        self.last_edge: float = 0.0
        
        # Signal Locking (User Strategy)
        self.active_signal: Optional[str] = None
        self.active_edge: float = 0.0
        self.active_signal_ts: Optional[int] = None # Minute of signal
        
        # Initialize CSV files
        self._init_csv()

        # LIVE TRADING CLIENT
        self.live_client = None
        self.live_trading_enabled = os.environ.get('LIVE_TRADING', 'false').lower() == 'true'
        
        if self.live_trading_enabled:
            self.log("[!] LIVE TRADING ENABLED! Initialization in progress...")
            try:
                from py_clob_client.client import ClobClient
                from py_clob_client.clob_types import ApiCreds, OrderArgs, AssetType, BalanceAllowanceParams
                self.live_client = ClobClient(
                    host="https://clob.polymarket.com",
                    chain_id=137,
                    key=os.environ.get('PRIVATE_KEY'),
                    creds=ApiCreds(
                        api_key=os.environ.get('CLOB_API_KEY'),
                        api_secret=os.environ.get('CLOB_API_SECRET'),
                        api_passphrase=os.environ.get('CLOB_PASSPHRASE')
                    )
                )
                self.log("[SUCCESS] LIVE TRADING CLIENT CONNECTED")
            except Exception as e:
                self.log(f"❌ FAILED TO CONNECT LIVE CLIENT: {e}")
                self.live_trading_enabled = False
    
    def _init_csv(self):
        """Initialize CSV log files."""
        if not os.path.exists(TRADES_FILE):
            with open(TRADES_FILE, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'slug', 'yes_token', 'no_token', 
                    'side', 'shares', 'p_up', 
                    'limit_price', 'fill_price', 'filled', 
                    'settlement_result', 'fees', 'pnl', 'balance'
                ])
        
        if not os.path.exists(EQUITY_FILE):
            with open(EQUITY_FILE, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'balance', 'peak_balance', 'open_pnl', 'wins', 'losses'])

    def _load_last_balance(self) -> float:
        """Load the last balance from the trades CSV if it exists."""
        
        # FIX: In Demo Mode, ignore the CSV (which might contain Real Wallet balance)
        is_live = os.environ.get('LIVE_TRADING', 'false').lower() == 'true'
        if not is_live:
             return 100.00
             
        try:
            if os.path.exists(TRADES_FILE):
                with open(TRADES_FILE, 'r') as f:
                    # Handle empty file or just header
                    lines = f.readlines()
                    if len(lines) > 1:
                        # Get last non-empty line
                        last_line = lines[-1].strip()
                        if last_line:
                            # CSV columns: ..., balance
                            parts = last_line.split(',')
                            last_bal = parts[-1] 
                            if last_bal:
                                print(f"[Init] Resuming from balance: ${float(last_bal):.2f}")
                                return float(last_bal)
        except Exception as e:
            print(f"[Init] Failed to load previous balance: {e}")
        
        print(f"[Init] Starting with fresh balance: ${DEMO_BALANCE:.2f}")
        return DEMO_BALANCE
    
    def log(self, msg):
        """Print with timestamp (ET) and log to file."""
        et_time = datetime.utcnow() - timedelta(hours=5)
        ts = et_time.strftime('%H:%M:%S')
        
        # Add visual indicator for live trading
        prefix = "[LIVE] " if self.live_trading_enabled else ""
        line = f"[{ts}] {prefix}{msg}"
        
        try:
            print(line)
        except UnicodeEncodeError:
            # Fallback for Windows consoles that don't support unicode
            print(line.encode('ascii', 'ignore').decode('ascii'))
        sys.stdout.flush()
        
        try:
            with open("logs/bot.log", "a") as f:
                f.write(line + "\n")
        except: pass
    
    def log_trade(self, order: DemoOrder):
        """Log trade to CSV."""
        try:
            result = "WIN" if order.pnl > 0 else "LOSS"
            with open(TRADES_FILE, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    order.timestamp.isoformat(),
                    self.market_slug or '',
                    order.yes_token_id,
                    order.no_token_id,
                    order.side.value,
                    order.shares,
                    round(order.p_up, 4),
                    order.limit_price,
                    order.fill_price,
                    order.fill_time.isoformat() if order.fill_time else '',
                    order.settlement_result or 'PENDING',
                    round(order.fees, 4),
                    round(order.pnl, 4),
                    round(self.balance, 2)
                ])
            self.log(f"Logged trade: {order.order_id} | {result} | PnL: ${order.pnl:+.2f}")
        except Exception as e:
            self.log(f"Error logging trade: {e}")
    
    def log_equity(self):
        """Log equity to CSV."""
        try:
            wins = sum(1 for o in self.orders if o.settled and o.pnl > 0)
            with open(EQUITY_FILE, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.utcnow().isoformat(),
                    round(self.balance, 2),
                    round(self.peak_balance, 2),
                    round((self.peak_balance - self.balance) / self.peak_balance * 100 if self.peak_balance > 0 else 0, 2),
                    len([o for o in self.orders if o.settled]),
                    wins
                ])
        except Exception as e:
            pass
    
    def can_trade(self) -> bool:
        """Check if we can place a new trade."""
        return self.pending_order is None and self.open_position is None
    
    def compute_edge(self, p_up: float, book: dict) -> tuple:
        """Compute edge for YES and NO sides."""
        yes_ask = book['yes_ask']
        no_ask = book['no_ask']
        
        # Edge for buying YES (bet on Up)
        edge_yes = p_up - yes_ask if yes_ask > 0 else -1
        
        # Edge for buying NO (bet on Down)
        edge_no = (1 - p_up) - no_ask if no_ask > 0 else -1
        
        return edge_yes, edge_no
    
    def place_demo_order(self, side: OrderSide, p_up: float, book: dict, btc_price: float):
        """Place a demo limit order near the bid."""
        self.order_counter += 1
        order_id = f"DEMO-{self.order_counter:04d}"
        
        # Smart Limit Order Logic
        # If spread is tight (<= 2 cents), Take Liquidity (Buy at Ask) to ensure fill.
        # If spread is wide, Make Liquidity (Bid + 1 cent) to save cost.
        
        if side == OrderSide.YES:
            spread = book['yes_ask'] - book['yes_bid']
            if spread <= 0.02: # Tight spread: Pay the Ask
                limit_price = book['yes_ask']
            else: # Wide spread: Bid + 0.01
                limit_price = book['yes_bid'] + 0.01
        else:
            spread = book['no_ask'] - book['no_bid']
            if spread <= 0.02: # Tight spread: Pay the Ask
                limit_price = book['no_ask']
            else: # Wide spread: Bid + 0.01
                limit_price = book['no_bid'] + 0.01
        
        limit_price = round(max(0.01, min(0.99, limit_price)), 3)

        # Risk Management & Min Order Size ($1.00)
        # 1. Determine Target Cost based on Risk Settings
        target_cost = self.balance * RISK_PER_TRADE
        
        # 2. Determine Minimum Shares to satisfy $1.00 rule
        # e.g. Price $0.27 -> Need 3.7 shares -> Ceil(3.7) = 4 shares ($1.08)
        min_shares_for_dollar = math.ceil(1.0 / limit_price)
        
        # 3. Polymarket also has a token-count minimum (usually 5 shares)
        # Requirement: Size (3) lower than the minimum: 5
        HARD_MIN_SHARES = 5
        
        # 4. Determine Shares by Risk
        target_shares = int(target_cost / limit_price)
        
        # 5. Take the highest floor (Enforce $1 Min OR 5 Token Min)
        shares = max(min_shares_for_dollar, target_shares, HARD_MIN_SHARES)
        
        # 6. Safety Check: Can we afford it?
        actual_cost = shares * limit_price
        if actual_cost > self.balance:
            self.log(f"Skipping trade: Balance ${self.balance:.2f} insufficient for min order ${actual_cost:.2f}")
            return

        # 6. Log if we are forcing higher risk
        if actual_cost > target_cost * 2.0: # If we double our risk just to trade
             self.log(f"Notice: Increased size to {shares} shares (${actual_cost:.2f}) to meet exchange minimums")

        bet_amount = shares * limit_price

        
        order = DemoOrder(
            order_id=order_id,
            timestamp=datetime.utcnow(),
            side=side,
            limit_price=limit_price,
            bet_amount=bet_amount,
            shares=shares,
            p_up=p_up,
            yes_bid=book['yes_bid'],
            yes_ask=book['yes_ask'],
            no_bid=book['no_bid'],
            no_ask=book['no_ask'],
            price_to_beat=self.price_to_beat,  # BTC at market open
            btc_at_entry=btc_price,
            yes_token_id=self.orderbook_poller.yes_token_id,
            no_token_id=self.orderbook_poller.no_token_id
        )
        
        self.pending_order = order
        self.orders.append(order)
        
        self.log(f"DEMO ORDER: {order_id} {side.value} {shares} shares @ {limit_price} (cost: ${bet_amount:.2f})")
        
        # Telegram notification
        tg.notify_order_placed(
            order_id=order_id,
            side=side.value,
            shares=shares,
            price=limit_price,
            btc_price=btc_price,
            market_slug=self.market_slug or "",
            balance=self.balance
        )
        
        # Start fill monitoring in background
        threading.Thread(target=self._monitor_fill, args=(order,), daemon=True).start()
    
    def _monitor_fill(self, order: DemoOrder):
        """Monitor order for fill over timeout period."""
        start_time = time.time()
        
        while time.time() - start_time < FILL_TIMEOUT_SECONDS:
            if not self.running:
                break
            
            book = self.orderbook_poller.get_orderbook()
            
            # Check if market ask <= limit price
            if order.side == OrderSide.YES:
                market_ask = book['yes_ask']
            else:
                market_ask = book['no_ask']
            
            if market_ask > 0 and market_ask <= order.limit_price:
                # FILLED
                order.filled = True
                order.fill_price = order.limit_price
                order.fill_time = datetime.utcnow()
                order.settlement_time = datetime.utcnow() + timedelta(minutes=SETTLEMENT_MINUTES)
                
                self.pending_order = None
                self.open_position = order
                
                self.log(f"FILLED: {order.order_id} {order.side.value} @ {order.fill_price}")
                
                 # TELEGRAM notification for fill
                tg.notify_order_filled(
                    order_id=order.order_id,
                    side=order.side.value,
                    shares=order.shares,
                    fill_price=order.fill_price,
                    btc_price=self.price_feed.get_current_price() or 0
                )

                # ======================================================
                # LIVE TRADING EXECUTION
                # ======================================================
                if self.live_trading_enabled and self.live_client:
                    try:
                        self.log(f"⚡ SENDING LIVE ORDER: {order.side.value} {order.shares} shares @ {order.fill_price}")
                        from py_clob_client.clob_types import OrderArgs
                        
                        token_id = order.yes_token_id if order.side == OrderSide.YES else order.no_token_id
                        if not token_id:
                            self.log("❌ LIVE EXECUTION FAILED: Missing token_id")
                        else:
                            # Create and sign order
                            # IMPORTANT: Polymarket uses FOK (Fill or Kill) or GTC. 
                            # We always BUY in this strategy (Buy YES or Buy NO)
                            resp = self.live_client.create_and_post_order(
                                OrderArgs(
                                    price=order.fill_price,
                                    size=float(order.shares),
                                    side="BUY", 
                                    token_id=token_id,
                                )
                            )
                            self.log(f"✅ LIVE ORDER SUBMITTED: TX {resp.get('transactionHash', 'N/A')}")
                            tg.send_message(f"🚨 **LIVE TRADE ENTERED** 🚨\nSide: {order.side.value}\nSize: {order.shares}\nPrice: {order.fill_price}")
                    except Exception as e:
                        self.log(f"❌ LIVE EXECUTION ERROR: {e}")
                        tg.send_message(f"⚠️ **LIVE EXECUTION FAILED** ⚠️\nError: {e}")
                # ======================================================
                
                # Schedule settlement check
                threading.Thread(
                    target=self._settle_position,
                    args=(order,),
                    daemon=True
                ).start()
                return
            
            time.sleep(1)
        
        # Timeout - cancel order
        order.cancelled = True
        self.pending_order = None
        self.log(f"CANCELLED: {order.order_id} - No fill after {FILL_TIMEOUT_SECONDS}s")
    
    def _settle_position(self, order: DemoOrder):
        """Settle position at market close time using Binance prices.
        
        Logic:
        - Price to Beat = BTC price at 15m window START (captured at market discovery)
        - Settle Price = BTC price at 15m window END (captured now)
        - If Settle > Price to Beat → YES wins
        - If Settle <= Price to Beat → NO wins
        """
        # Calculate market close time from the slug timestamp
        # Slug format: btc-updown-15m-{unix_timestamp}
        # Market opens at that timestamp and closes 15 minutes later
        try:
            if self.market_slug:
                market_open_ts = int(self.market_slug.split('-')[-1])
                market_close_ts = market_open_ts + 900  # 15 minutes in seconds
                now_ts = int(time.time())
                wait_seconds = max(0, market_close_ts - now_ts + 2)  # +2 sec buffer
                self.log(f"Waiting {wait_seconds}s until market close (ts={market_close_ts})")
            else:
                wait_seconds = SETTLEMENT_MINUTES * 60  # Fallback
        except Exception as e:
            self.log(f"Error calculating settlement time: {e}")
            wait_seconds = SETTLEMENT_MINUTES * 60  # Fallback
        
        time.sleep(wait_seconds)
        
        if not self.running:
            return
        
        # Get BTC price at settlement from Binance
        btc_settle = self.price_feed.get_current_price() or order.btc_at_entry
        order.btc_at_settle = btc_settle
        
        # Use Binance price for settlement decision
        # Price to Beat was captured at market discovery (refresh_market)
        price_to_beat = order.price_to_beat
        
        if price_to_beat <= 0:
            # Fallback: use entry price if no price_to_beat was set
            price_to_beat = order.btc_at_entry
            self.log(f"WARNING: Using entry price as price_to_beat fallback: ${price_to_beat:,.2f}")
        
        # Determine outcome: YES wins if settle > price_to_beat, else NO wins
        if btc_settle > price_to_beat:
            market_result = "YES"
        else:
            market_result = "NO"
        
        order.settlement_result = market_result
        won = (order.side.value == market_result)
        
        self.log(f"BINANCE SETTLEMENT: ${price_to_beat:,.2f} -> ${btc_settle:,.2f} = {market_result}")
        
        if not self.running:
            return
        
        # Calculate PnL
        # Entry cost = shares * fill_price = bet_amount
        # Win payout = shares * $1.00 = shares
        # Loss = -entry_cost
        entry_cost = order.bet_amount  # Already shares * price
        fees = entry_cost * FEE_RATE * 2  # Entry + exit fee
        order.fees = fees
        
        if won:
            payout = order.shares * 1.0  # Each share pays $1 on win
            order.pnl = payout - entry_cost - fees
            self.log(f"WIN: {order.order_id} ({order.shares} shares) | PtB ${price_to_beat:,.0f} -> ${btc_settle:,.0f} | PnL: ${order.pnl:+.2f}")
        else:
            order.pnl = -entry_cost - fees
            self.log(f"LOSS: {order.order_id} ({order.shares} shares) | PtB ${price_to_beat:,.0f} -> ${btc_settle:,.0f} | PnL: ${order.pnl:+.2f}")
        
        # Update balance
        self.balance += order.pnl
        self.peak_balance = max(self.peak_balance, self.balance)
        
        order.settled = True
        self.open_position = None
        
        # Log
        self.log_trade(order)
        self.log_equity()
        
        self.log(f"BALANCE: ${self.balance:.2f} (Peak: ${self.peak_balance:.2f})")
        
        # Telegram notification
        tg.notify_settlement(
            order_id=order.order_id,
            side=order.side.value,
            shares=order.shares,
            result="WIN" if won else "LOSS",
            pnl=order.pnl,
            price_to_beat=price_to_beat,
            btc_settle=btc_settle,
            new_balance=self.balance,
            fees=order.fees
        )
    
    def on_candle_close(self, candle):
        """Handle candle close - compute features and check for signals."""
        # Always add specific candle to feature engine first!
        self.feature_engine.add_candle(candle)

        # ------------------------------------------------------------------
        # TIMING OPTIMIZATION: Only trade at 00, 15, 30, 45 (or +1 min)
        # ------------------------------------------------------------------
        # STRICT BACKTEST TIMING (User Request)
        # ------------------------------------------------------------------
        # 1. Signal at :00 (Snapshot) called "Locked Signal"
        # 2. Execution Window: 5 Minutes (Hunt for Price)
        # 3. UI: Show SNAPSHOT RSI (Static) - Do not show 1m fluctuations
        
        current_minute = datetime.utcnow().minute
        minute_in_cycle = current_minute % 15
        
        # RESET Signal if we are deep in the cycle (> 10 minutes in)
        if minute_in_cycle > 10 and self.active_signal:
             self.log("Signal Limit Reached (10m). Stop Hunting.")
             self.active_signal = None
             self.active_edge = 0.0
             
        # CALCULATE Signal (Only at Minute 0)
        # We enforce STRICT :00 calculation.
        if minute_in_cycle == 0:
            # Create feature snapshot
            features = self.feature_engine.compute_features()
            if features:
                 prob = self.feature_engine.predict_probability(features)
                 
                 # UPDATE SNAPSHOT UI METRICS
                 self.last_rsi = getattr(features, 'rsi_14', 50.0)
                 self.last_trend = getattr(features, 'dist_ema_50', 0.0)
                 
                 # Only lock if we haven't locked yet for this cycle
                 if not self.active_signal or self.active_signal_ts != current_minute:
                     raw_signal, edge = self.feature_engine.check_signal(features, prob)
                     if raw_signal:
                         self.active_signal = raw_signal
                         self.active_edge = edge
                         self.active_signal_ts = current_minute
                         self.last_prob = prob  # LOCK probability with signal!
                         self.log(f"⚔️ SIGNAL LOCKED: {raw_signal} (Edge: {edge:.2f}) - Hunting for Entry (10m)...")
                     else:
                         self.active_signal = None # Clear if no signal 
                     
        # If we are NOT in the execution window (0-10), we stop here.
        # Unless we want to log "Waiting..."
        if minute_in_cycle > 10:
            if current_minute % 5 == 0 and datetime.utcnow().second < 10:
                self.log(f"Waiting for 15m close... (Current: :{current_minute:02d} | RSI: {self.last_rsi:.2f})")
            return 

        # EXECUTION (Only if we have a Locked Signal)
        if not self.active_signal:
             if minute_in_cycle == 0 and datetime.utcnow().second % 10 == 0:
                 rsi_val = getattr(features, 'rsi_14', 0) if features else 0
                 self.log(f"Waiting for Signal... (RSI: {rsi_val:.2f})")
             return

        # We have a signal. Now check Orderbook for Entry.
        book = self.orderbook_poller.get_orderbook()
        if not book.get('yes_ask') or not book.get('no_ask'):
            return
            
        signal = self.active_signal
        
        # Can we trade?
        if not self.can_trade():
            return
        
        # Compute edge from real orderbook
        # Note: We use the LOCKED probability (from :00) or current?
        # User wants "Signal at :00". So we use the implied prob from :00?
        # Actually, compute_edge uses 'prob' relative to market price.
        # Let's use the 'prob' we locked (self.last_prob)
        edge_yes, edge_no = self.compute_edge(self.last_prob, book)
        
        # Check if edge meets threshold
        if signal == "YES" and edge_yes >= EDGE_THRESHOLD:
            if book['yes_bid'] > 0 and book['yes_ask'] > 0:
                btc_price = self.price_feed.get_current_price() or features.close
                self.log(f"SIGNAL: YES (p={self.last_prob:.3f}, edge={edge_yes:.3f})")
                self.place_demo_order(OrderSide.YES, self.last_prob, book, btc_price)
        
        elif signal == "NO" and edge_no >= EDGE_THRESHOLD:
            if book['no_bid'] > 0 and book['no_ask'] > 0:
                btc_price = self.price_feed.get_current_price() or features.close
                self.log(f"SIGNAL: NO (p={self.last_prob:.3f}, edge={edge_no:.3f})")
                self.place_demo_order(OrderSide.NO, self.last_prob, book, btc_price)
        
        else:
            # Log why we didn't trade
            if signal == "YES" and edge_yes < EDGE_THRESHOLD:
                self.log(f"⚠️ SKIP: Edge too low ({edge_yes:.3f} < {EDGE_THRESHOLD})")
            elif signal == "NO" and edge_no < EDGE_THRESHOLD:
                self.log(f"⚠️ SKIP: Edge too low ({edge_no:.3f} < {EDGE_THRESHOLD})")
    
    def refresh_market(self):
        """Refresh market discovery and capture price_to_beat from Binance."""
        self.log("Refreshing market discovery...")
        market = resolve_market()
        
        if market and market.get('yes_token_id'):
            self.market_slug = market['slug']
            self.orderbook_poller.yes_token_id = market['yes_token_id']
            self.orderbook_poller.no_token_id = market['no_token_id']
            self.orderbook_poller.market_slug = market['slug']
            
            # FORCE IMMEDIATE UPDATE: Don't wait for background thread
            self.log("Forcing immediate orderbook update...")
            self.orderbook_poller.poll_once()
            
            # Extract market open timestamp from slug
            # Slug format: btc-updown-15m-{unix_timestamp}
            try:
                market_open_ts = int(market['slug'].split('-')[-1])
            except:
                market_open_ts = None
            
            # Capture "Price to Beat" from Binance at EXACT 15m window start
            # This queries the Binance API for the candle at that exact timestamp
            btc_at_start = self.price_feed.get_price_at_15m_start(market_open_ts)
            
            if btc_at_start and btc_at_start > 0:
                self.price_to_beat = btc_at_start
                self.log(f"Market: {market['slug']} | Price to Beat (Binance @{market_open_ts}): ${self.price_to_beat:,.2f}")
            else:
                # Fallback to current price if API fails
                btc_now = self.price_feed.get_current_price()
                if btc_now and btc_now > 0:
                    self.price_to_beat = btc_now
                    self.log(f"Market: {market['slug']} | Price to Beat (current): ${self.price_to_beat:,.2f}")
                else:
                    self.price_to_beat = 0.0
                    self.log(f"WARNING: Could not get price_to_beat for {market['slug']}")
            return True
        else:
            self.log("No valid future market found. Pausing trading...")
            # Clear tokens so we don't trade old market
            self.orderbook_poller.yes_token_id = None
            self.orderbook_poller.no_token_id = None
            self.market_slug = None
            self.price_to_beat = 0.0
            return False
    
    def start(self):
        """Start the paper trader."""
        self.running = True
        
        if self.live_trading_enabled:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] " + "=" * 60)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [!] LIVE TRADING ACTIVE | REAL MONEY AT RISK [!]")
            
            # Fetch Real Balance
            if self.live_client:
                try:
                    from py_clob_client.clob_types import AssetType, BalanceAllowanceParams
                    res = self.live_client.get_balance_allowance(
                        params=BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
                    )
                    real_bal = float(res['balance']) / 1e6 # USDC has 6 decimals
                    
                    # SYNC INTERNAL BALANCE WITH REAL WALLET
                    self.balance = real_bal
                    
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] LIVE ACCOUNT BALANCE: ${self.balance:,.2f}")
                except Exception as e:
                     print(f"[{datetime.now().strftime('%H:%M:%S')}] Failed to sync wallet balance: {e}")

            print(f"[{datetime.now().strftime('%H:%M:%S')}] " + "=" * 60)
        else:
            self.log("=" * 60)
            self.log("REAL POLYMARKET PAPER TRADER")
            
            # Reset to Demo Balance (Avoid showing real wallet balance)
            self.balance = 100.00
            
            self.log(f"DEMO Balance: ${self.balance:.2f} | REAL Prices")
            self.log("=" * 60)
        
        # Resolve market
        if not self.refresh_market():
            self.log("No market found. Using simulated fallback...")
        
        # Start price feed
        self.log("Starting BTC price feed...")
        self.price_feed.add_callback(self.on_candle_close)
        self.price_feed.start(preload=True)
        
        # SYNC HISTORY: Feed preloaded candles to Feature Engine
        with self.price_feed._lock:
            history_copy = list(self.price_feed.candles)
            
        self.log(f"Feeding {len(history_copy)} historical candles to Feature Engine...")
        for candle in history_copy:
            self.feature_engine.add_candle(candle)
            
        # Verify engine state
        initial_features = self.feature_engine.compute_features()
        if initial_features:
            rsi = getattr(initial_features, 'rsi_14', 50.0)
            self.last_rsi = rsi
            self.last_trend = getattr(initial_features, 'dist_ema_50', 0.0)
            self.log(f"Initial State Verified: RSI={rsi:.2f}")
        else:
            self.log("Warning: Feature Engine still warming up.")
        
        # Start orderbook poller
        self.log("Starting orderbook polling...")
        self.orderbook_poller.start_polling()
        
        # Market refresh thread
        def refresh_loop():
            while self.running:
                # Calculate seconds until next 15m boundary
                now = time.time()
                next_boundary = ((now // 900) + 1) * 900
                # PRE-FETCH: Wake up 5 seconds BEFORE the boundary to resolve next market
                sleep_seconds = next_boundary - now - 5
                
                # Cap sleep at 300s (5 mins) just in case
                sleep_seconds = min(sleep_seconds, 300)
                
                # Sleep at least A BIT
                if sleep_seconds < 1:
                    sleep_seconds = 1
                
                self.log(f"Next market rotation in {sleep_seconds:.0f}s (Pre-fetch)")
                time.sleep(sleep_seconds)
                
                self.refresh_market()
        
        threading.Thread(target=refresh_loop, daemon=True).start()
        
        # Display loop
        def display_loop():
            while self.running:
                book = self.orderbook_poller.get_orderbook()
                btc = self.price_feed.get_current_price()
                
                if book.get('yes_ask'):
                    btc_str = f"${btc:,.0f}" if btc else "Wait..."
                    
                    # Calculate data age
                    age_str = "0s"
                    if book.get('last_update'):
                        try:
                            last_ts = datetime.fromisoformat(book['last_update'])
                            age = (datetime.utcnow() - last_ts).total_seconds()
                            age_str = f"{age:.1f}s"
                        except:
                            pass
                            
                    et_time = datetime.utcnow() - timedelta(hours=5)
                    # Trend logic (SNAPSHOT VALUES)
                    last_rsi = getattr(self, 'last_rsi', 50.0)
                    last_trend = getattr(self, 'last_trend', 0.0)
                    trend_str = "UP" if last_trend > 0 else "DOWN"
                    
                    # Print new line every 10 seconds so user sees movement
                    print(f"[{et_time.strftime('%H:%M:%S')}] "
                          f"BTC: {btc_str} | "
                          f"RSI (Snap): {last_rsi:.2f} | "
                          f"Trend: {trend_str} | "
                          f"YES: {book['yes_bid']:.2f}/{book['yes_ask']:.2f} | "
                          f"NO: {book['no_bid']:.2f}/{book['no_ask']:.2f} | "
                          f"Bal: ${self.balance:.2f}")
                    sys.stdout.flush()

                    # WATCHDOG: If prices are 0.00/0.00 (Empty Orderbook)
                    if book['yes_ask'] <= 0.01 and book['no_ask'] <= 0.01:
                        self.empty_ticks = getattr(self, 'empty_ticks', 0) + 1
                        if self.empty_ticks > 5: # 50 seconds
                            print(f"[{et_time.strftime('%H:%M:%S')}] Watchdog: Orderbook empty for 50s. Forcing Refresh...")
                            self.empty_ticks = 0
                            self.refresh_market()
                    else:
                        self.empty_ticks = 0
                else:
                    et_time = datetime.utcnow() - timedelta(hours=5)
                    # Print waiting message if book is empty
                    print(f"\r[{et_time.strftime('%H:%M:%S')}] Waiting for orderbook...", end='')
                
                
                    # EXPORT STATE (For Dashboard)
                    try:
                        state = {
                            "timestamp": datetime.utcnow().isoformat(),
                            "status": "running",
                            "btc_price": btc,
                            "market_slug": self.market_slug,
                            "balance": self.balance,
                            "orderbook": book,
                            "price_to_beat": self.price_to_beat,
                            "open_position": None,
                            "empty_ticks": self.empty_ticks
                        }
                        
                        if self.open_position:
                            state["open_position"] = {
                                "side": self.open_position.side.value,
                                "entry_price": self.open_position.fill_price,
                                "shares": self.open_position.shares,
                                "order_id": self.open_position.order_id
                            }
                            
                        # Atomic write
                        with open("logs/bot_state.json.tmp", "w") as f:
                            json.dump(state, f)
                        os.replace("logs/bot_state.json.tmp", "logs/bot_state.json")
                    except Exception as e:
                        pass


                time.sleep(1) # Faster display update
        
        threading.Thread(target=display_loop, daemon=True).start()
        
        self.log("Paper trader running. Press Ctrl+C to stop.")
    
    def stop(self):
        """Stop the paper trader."""
        self.running = False
        self.price_feed.stop()
        self.orderbook_poller.stop_polling()
        self.log("Paper trader stopped.")
        self.log(f"Final Balance: ${self.balance:.2f}")


def main():
    trader = RealPolymarketPaperTrader()
    trader.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        trader.stop()


if __name__ == "__main__":
    main()
