
"""
Unified Strategy Logic
Central definition of trading rules to ensure Backtest/Live parity.
"""
from typing import Tuple, Optional

# Constants
RSI_OVERSOLD_DEFAULT = 43
RSI_OVERBOUGHT_DEFAULT = 58

# Dynamic Adjustment Constants
RSI_BUY_DOWNTREND = 38
RSI_SELL_UPTREND = 62

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
