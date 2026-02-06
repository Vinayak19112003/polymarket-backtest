
import pytest
from src.features.strategy import (
    check_mean_reversion_signal, 
    get_mean_reversion_thresholds,
    RSI_OVERSOLD_DEFAULT, RSI_OVERBOUGHT_DEFAULT,
    RSI_BUY_DOWNTREND, RSI_SELL_UPTREND
)

class TestMeanReversionThresholds:
    def test_downtrend_thresholds(self):
        """Test strict buy thresholds during downtrend."""
        buy, sell = get_mean_reversion_thresholds(dist_ema_50=-0.01)
        assert buy == RSI_BUY_DOWNTREND
        assert sell == RSI_OVERBOUGHT_DEFAULT

    def test_uptrend_thresholds(self):
        """Test strict sell thresholds during uptrend."""
        buy, sell = get_mean_reversion_thresholds(dist_ema_50=0.01)
        assert buy == RSI_OVERSOLD_DEFAULT
        assert sell == RSI_SELL_UPTREND

    def test_neutral_thresholds(self):
        """Test fallback thresholds (or slight edge case)."""
        # Exact 0 dist is treated as uptrend logic in current implementation (elif dist > 0: ... else default)
        # Actually implementation is: if < 0: ... elif > 0: ... else: default.
        buy, sell = get_mean_reversion_thresholds(dist_ema_50=0.0)
        assert buy == RSI_OVERSOLD_DEFAULT
        assert sell == RSI_OVERBOUGHT_DEFAULT

class TestSignalGeneration:
    def test_buy_signal(self):
        """Test YES signal generation (Oversold)."""
        # Normal context (dist=0) -> Buy < 43
        rsi = 30
        signal, edge = check_mean_reversion_signal(rsi_14=rsi, dist_ema_50=0)
        assert signal == 'YES'
        assert edge > 0

    def test_sell_signal(self):
        """Test NO signal generation (Overbought)."""
        # Normal context (dist=0) -> Sell > 58
        rsi = 70
        signal, edge = check_mean_reversion_signal(rsi_14=rsi, dist_ema_50=0)
        assert signal == 'NO'
        assert edge > 0

    def test_no_signal_neutral(self):
        """Test RSI between thresholds."""
        rsi = 50
        signal, edge = check_mean_reversion_signal(rsi_14=rsi, dist_ema_50=0)
        assert signal is None
        assert edge == 0.0

class TestEdgeCalculation:
    def test_edge_increases_with_extremity(self):
        """More extreme RSI should yield higher edge."""
        # Buy side
        _, edge_30 = check_mean_reversion_signal(30, 0)
        _, edge_20 = check_mean_reversion_signal(20, 0)
        assert edge_20 > edge_30
        
        # Sell side
        _, edge_70 = check_mean_reversion_signal(70, 0)
        _, edge_80 = check_mean_reversion_signal(80, 0)
        assert edge_80 > edge_70

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
