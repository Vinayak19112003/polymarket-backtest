
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.bot.features import RealtimeFeatureEngine

class TestFeatureEngine:
    def setup_method(self):
        """Initialize fresh engine for each test."""
        self.engine = RealtimeFeatureEngine()
        self.start_time = datetime(2025, 1, 1, 0, 0, 0)
        
    def generate_synthetic_candles(self, n=500, trend=0.0):
        """Generate N synthetic 1m candles."""
        candles = []
        price = 100.0
        for i in range(n):
            ts = self.start_time + timedelta(minutes=i)
            # Random walk with trend
            change = np.random.normal(0, 0.1) + trend
            price += change
            
            candles.append({
                'timestamp': ts,
                'open': price,
                'high': price + 0.1,
                'low': price - 0.1,
                'close': price + 0.05,
                'volume': 1000
            })
        return candles

    def test_initialization(self):
        assert len(self.engine.candles) == 0
        assert self.engine.model_data is None # Should default to None in simple mode

    def test_candle_accumulation(self):
        candles = self.generate_synthetic_candles(10)
        for c in candles:
            self.engine.add_candle(c)
        assert len(self.engine.candles) == 10

    def test_features_computation(self):
        # Need enough data for 15m resampling and RSI(14) calculation
        # AND satisfying REQUIRED_CANDLES (3000)
        candles = self.generate_synthetic_candles(3500)
        for c in candles:
            self.engine.add_candle(c)
            
        features = self.engine.compute_features()
        assert features is not None
        assert 0 <= features.rsi_14 <= 100
        assert isinstance(features.dist_ema_50, float)

    def test_insufficient_data(self):
        # 10 minutes is not enough for 15m resampling of indicators
        candles = self.generate_synthetic_candles(10)
        for c in candles:
            self.engine.add_candle(c)
            
        # Should handle gracefully, might return None or features with defaults
        features = self.engine.compute_features()
        if features:
            # If it returns features, RSI might be 50.0 (default)
            assert features.rsi_14 == 50.0
        else:
            assert features is None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
