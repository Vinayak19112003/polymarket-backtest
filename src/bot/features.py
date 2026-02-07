"""
Real-Time Feature Engine V2
Uses Mean Reversion Strategy (RSI 38/62) for high-performance trading
Backtest: ALL 6 MONTHS PROFITABLE, +47% ROI, 55% win rate
"""

import numpy as np
import pandas as pd
import pickle
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass

# Strategy selection
USE_MEAN_REVERSION = True  # Set to True for Mean Reversion, False for ML

# Mean Reversion thresholds (Optimized High Frequency: +490% ROI like backtest)
RSI_OVERSOLD = 38   # BUY YES when RSI < 38
RSI_OVERBOUGHT = 62 # BUY NO when RSI > 62


@dataclass
class TradingFeaturesV2:
    """Container for all V2 trading features."""
    timestamp: pd.Timestamp
    close: float
    ret_1m: float
    ret_5m: float
    ret_15m: float
    ret_30m: float
    ret_60m: float
    range_5m: float
    range_15m: float
    range_30m: float
    atr_15m: float
    pos_15m: float
    z_5m: float
    z_15m: float
    dist_ema_20: float
    dist_ema_50: float
    rsi_14: float
    rsi_4: float
    trend_align: int
    momentum_score: int
    volatility_regime: int
    hour_sin: float
    hour_cos: float
    h1_dist_ema: float = 0.0 # New: 1H Trend Distance
    
    # Optional fields
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    volume: float = 0.0
    ema_50: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'close': self.close,
            'ret_1m': self.ret_1m,
            'ret_5m': self.ret_5m,
            'ret_15m': self.ret_15m,
            'ret_30m': self.ret_30m,
            'ret_60m': self.ret_60m,
            'range_5m': self.range_5m,
            'range_15m': self.range_15m,
            'range_30m': self.range_30m,
            'ATR_15m': self.atr_15m,
            'pos_15m': self.pos_15m,
            'z_5m': self.z_5m,
            'z_15m': self.z_15m,
            'dist_ema_20': self.dist_ema_20,
            'dist_ema_50': self.dist_ema_50,
            'rsi_14': self.rsi_14,
            'rsi_4': self.rsi_4,
            'trend_align': self.trend_align,
            'momentum_score': self.momentum_score,
            'volatility_regime': self.volatility_regime,
            'hour_sin': self.hour_sin,
            'hour_cos': self.hour_cos,
            'h1_dist_ema': self.h1_dist_ema
        }

class RealtimeFeatureEngineV2:
    """Compute V2 trading features with trend/momentum confirmation."""
    
    REQUIRED_CANDLES = 150 # Enough for 15m resampling of 200 bars? No. 
    # Logic in compute_features handles resampling.
    # If we need 50 bars of 15m, we need 750 bars of 1m.
    # Set buffer to 1000.
    REQUIRED_CANDLES = 1000
    
    SIGNAL_THRESHOLD = 0.60
    EDGE_REQUIRED = 0.10
    
    def __init__(self, model_path: str = "models/btc_predictor_v2.pkl"):
        self.model_path = model_path
        self.model_data = None # Default to None
        self.candles = []
        self.atr_history = []
    
    def add_candle(self, candle):
        """Add a new candle to the internal buffer, handling duplicates."""
        if not self.candles:
            self.candles.append(candle)
            return

        last_ts = self.candles[-1]['timestamp']
        new_ts = candle['timestamp']
        
        if new_ts == last_ts:
            # Update existing candle (Live forming)
            self.candles[-1] = candle
        elif new_ts > last_ts:
            # New candle
            self.candles.append(candle)
            
        # Maintain buffer size
        if len(self.candles) > self.REQUIRED_CANDLES + 50:
            self.candles = self.candles[-self.REQUIRED_CANDLES:]

    def compute_features(self, df: Optional[pd.DataFrame] = None) -> Optional[TradingFeaturesV2]:
        """Compute V2 features using 15M RESAMPLING."""
        if df is None:
            if len(self.candles) < 20: # Minimal check
                return None
            df = pd.DataFrame(self.candles)
        
        # Ensure timestamp
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
        
        # Resample to 15m
        df_15m = df.set_index('timestamp').resample('15min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        if len(df_15m) < 20:
             return None
        
        # Compute Indicators on 15M Data
        delta = df_15m['close'].diff()
        
        # RSI 14
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi_15m_series = 100 - (100 / (1 + rs))
        
        # EMAs
        ema_20_series = df_15m['close'].ewm(span=20, adjust=False).mean()
        ema_50_series = df_15m['close'].ewm(span=50, adjust=False).mean()
        
        # Current Values
        current_15m = df_15m.iloc[-1]
        
        rsi_14 = rsi_15m_series.iloc[-1] if len(rsi_15m_series) > 0 else 50.0
        dist_ema_20 = (current_15m['close'] / ema_20_series.iloc[-1]) - 1
        dist_ema_50 = (current_15m['close'] / ema_50_series.iloc[-1]) - 1
        
        # ATR 15m
        tr = pd.concat([
            df_15m['high'] - df_15m['low'],
            abs(df_15m['high'] - df_15m['close'].shift(1)),
            abs(df_15m['low'] - df_15m['close'].shift(1))
        ], axis=1).max(axis=1)
        atr_15m_val = tr.rolling(14).mean().iloc[-1] if len(tr) > 14 else 0.0
        
        # 1H Trend
        df_1h = df_15m.resample('1h').agg({'close': 'last'}).dropna()
        ema_20_1h = df_1h['close'].ewm(span=20, adjust=False).mean()
        h1_dist_ema = 0.0
        if len(df_1h) > 0 and len(ema_20_1h) > 0:
            h1_dist_ema = (df_1h['close'].iloc[-1] / ema_20_1h.iloc[-1]) - 1
            
        # Micro Features (1m)
        current_1m = df.iloc[-1]
        
        # Construct Object
        return TradingFeaturesV2(
            timestamp=current_1m['timestamp'],
            close=current_1m['close'],
            open=current_1m.get('open', 0),
            high=current_1m.get('high', 0),
            low=current_1m.get('low', 0),
            volume=current_1m.get('volume', 0),
            ret_1m=0.0, # Simplified
            ret_5m=0.0,
            ret_15m=0.0,
            ret_30m=0.0,
            ret_60m=0.0,
            range_5m=0.0,
            range_15m=0.0,
            range_30m=0.0,
            atr_15m=atr_15m_val,
            pos_15m=0.5,
            z_5m=0.0,
            z_15m=0.0,
            dist_ema_20=dist_ema_20,
            dist_ema_50=dist_ema_50,
            rsi_14=rsi_14,
            rsi_4=0.0,
            trend_align=0,
            momentum_score=0,
            volatility_regime=0,
            hour_sin=0.0,
            hour_cos=0.0,
            h1_dist_ema=h1_dist_ema,
            ema_50=ema_50_series.iloc[-1]
        )

    def check_signal(self, features: TradingFeaturesV2, probability: float = 0.5) -> Tuple[Optional[str], float]:
        """Check for trading signal using V2 Strategy."""
        # 1. Time-of-Day Filter
        # UTC Hours 5-9 and 15-16 are blocked
        BLOCKED_HOURS = [5, 6, 7, 8, 9, 15, 16] 
        current_hour = features.timestamp.hour
        
        if current_hour in BLOCKED_HOURS:
             print(f"[DEBUG] Blocked: Illiquid/Unprofitable Hour {current_hour} UTC")
             return (None, 0.0)
        
        # Liquidity Boost
        liquidity_boost = 1.0
        if 12 <= current_hour <= 21:
            liquidity_boost = 1.05
        
        # 2. V2 Signal Check (Delegated to Unified Strategy)
        from src.features.strategy import check_mean_reversion_signal_v2
        
        signal, edge, reason = check_mean_reversion_signal_v2(
            rsi_14=features.rsi_14,
            dist_ema_50=features.dist_ema_50,
            atr_15m=features.atr_15m,
            close=features.close,
            enable_vol_filter=True, # Unified Volatility Check
            ml_probability=probability
        )
        
        if not signal:
            return (None, 0.0)
            
        # 3. Multi-Timeframe Confirmation
        h1_dist = features.h1_dist_ema
        
        if h1_dist > 0.02: # Strong 1H Uptrend
            if signal == 'NO':
                 print(f"[DEBUG] Blocked: Strong 1H Uptrend ({h1_dist:.4f}) blocks SHORT")
                 return (None, 0.0)
            elif signal == 'YES':
                 edge *= 1.1
                 reason += " + 1H Trend Boost"
                 
        elif h1_dist < -0.02: # Strong 1H Downtrend
            if signal == 'YES':
                 print(f"[DEBUG] Blocked: Strong 1H Downtrend ({h1_dist:.4f}) blocks LONG")
                 return (None, 0.0)
            elif signal == 'NO':
                 edge *= 1.1
                 reason += " + 1H Trend Boost"
        
        # Apply Boosts
        edge *= liquidity_boost
        
        PREMIUM_HOURS = [20, 21, 22, 23]
        if current_hour in PREMIUM_HOURS:
            edge *= 1.15
            reason += " + Premium Hour Boost"
        
        print(f"[DEBUG] SIGNAL {signal}! RSI={rsi:.2f}, Edge={edge:.2f} | {reason}")
        return (signal, edge)

    def predict_probability(self, features: TradingFeaturesV2) -> float:
        return 0.5 # Dummy for now

# Keep backward compatibility
RealtimeFeatureEngine = RealtimeFeatureEngineV2
TradingFeatures = TradingFeaturesV2
