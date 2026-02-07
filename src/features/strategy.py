
"""
Unified Strategy Logic
Central definition of trading rules to ensure Backtest/Live parity.
"""
from typing import Tuple, Optional

# Constants
RSI_OVERSOLD_DEFAULT = 38  # Stricter - matches profitable downtrend threshold
RSI_OVERBOUGHT_DEFAULT = 62  # Stricter - matches profitable uptrend threshold

# Dynamic Adjustment Constants
RSI_BUY_DOWNTREND = 35 # Even stricter in downtrend
RSI_SELL_UPTREND = 65 # Even stricter in uptrend

def get_mean_reversion_thresholds(dist_ema_50: float) -> Tuple[int, int]:
    """
    Calculate dynamic RSI thresholds based on EMA trend distance.
    
    Args:
        dist_ema_50: (Price / EMA_50) - 1. Negative means price < EMA (Downtrend).
        
    Returns:
        (rsi_buy_threshold, rsi_sell_threshold)
    """
    # Default
    rsi_buy = RSI_OVERSOLD_DEFAULT
    rsi_sell = RSI_OVERBOUGHT_DEFAULT
    
    # Logic: 
    # - Downtrend (dist_ema < 0): Stricter BUY (38), Normal SELL (58)
    # - Uptrend (dist_ema > 0): Normal BUY (43), Stricter SELL (62)
    
    if dist_ema_50 < 0: # Downtrend
        rsi_buy = RSI_BUY_DOWNTREND
    elif dist_ema_50 > 0: # Uptrend
        rsi_sell = RSI_SELL_UPTREND
        
    return rsi_buy, rsi_sell

def check_mean_reversion_signal(rsi_14: float, dist_ema_50: float) -> Tuple[Optional[str], float]:
    """
    Determine trade signal based on RSI and Dynamic Thresholds.
    Returns: (Signal 'YES'/'NO' or None, Edge)
    """
    rsi_buy, rsi_sell = get_mean_reversion_thresholds(dist_ema_50)
    
    # Oversold - expect bounce UP (YES)
    if rsi_14 < rsi_buy:
        edge = (rsi_buy - rsi_14) / rsi_buy
        return ('YES', min(0.5, edge))
    
    # Overbought - expect pullback DOWN (NO)
    elif rsi_14 > rsi_sell:
        edge = (rsi_14 - rsi_sell) / (100 - rsi_sell)
        return ('NO', min(0.5, edge))
        
    return (None, 0.0)

def get_volatility_regime(atr_15m: float, close: float) -> str:
    """
    Determine volatility regime based on ATR percentage.
    Thresholds: <0.3% Low, >0.8% High
    """
    if close == 0: return 'normal'
    
    atr_pct = (atr_15m / close) * 100
    
    if atr_pct < 0.3:
        return 'low'
    elif atr_pct > 0.8:
        return 'high'
    return 'normal'

def check_mean_reversion_signal_v2(
    rsi_14: float, 
    dist_ema_50: float, 
    atr_15m: Optional[float] = None, 
    close: Optional[float] = None,
    enable_vol_filter: bool = True,
    ml_probability: Optional[float] = None
) -> Tuple[Optional[str], float, str]:
    """
    Enhanced V2 Signal Check with Volatility filtering AND ML Confirmation.
    Returns: (Signal, Edge, Reason)
    """
    signal, edge = check_mean_reversion_signal(rsi_14, dist_ema_50)
    reason = "V2 Enhanced (Base)"
    
    if not signal:
        return (None, 0.0, "No Base Signal")
        
    # Apply Volatility Filter
    if enable_vol_filter and atr_15m is not None and close is not None:
        regime = get_volatility_regime(atr_15m, close)
        
        if regime == 'high':
            # Skip high volatility
            return (None, 0.0, f"Blocked: High Volatility (Regime: {regime})")
            
        elif regime == 'low':
            # Boost edge in low volatility (more predictable)
            edge *= 1.2
            reason = f"Booster: Low Volatility (Regime: {regime})"
            
    # Apply ML Filter (Hybrid)
    if ml_probability is not None:
        if signal == 'YES' and ml_probability < 0.4:
            return (None, 0.0, f"Blocked: ML bearish ({ml_probability:.2f})")
        elif signal == 'NO' and ml_probability > 0.6:
            return (None, 0.0, f"Blocked: ML bullish ({ml_probability:.2f})")
        elif (signal == 'YES' and ml_probability > 0.6) or (signal == 'NO' and ml_probability < 0.4):
            edge *= 1.15
            reason += f" + ML Confirmed ({ml_probability:.2f})"
            
    return (signal, min(0.5, edge), reason)
