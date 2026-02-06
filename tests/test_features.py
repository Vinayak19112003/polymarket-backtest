"""
Test ML Feature Engineering
"""
import pytest
import pandas as pd
import numpy as np
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bot.feature_engineering import (
    calculate_returns,
    calculate_volatility,
    calculate_technical_indicators,
    get_feature_columns
)


@pytest.fixture
def sample_ohlcv_data():
    """Create sample OHLCV data for testing."""
    np.random.seed(42)
    n = 200
    
    # Generate realistic price data
    prices = 50000 + np.cumsum(np.random.randn(n) * 100)
    
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=n, freq='1min'),
        'open': prices,
        'high': prices + np.abs(np.random.randn(n) * 50),
        'low': prices - np.abs(np.random.randn(n) * 50),
        'close': prices + np.random.randn(n) * 30,
        'volume': np.random.randint(100, 1000, n)
    })
    return df


class TestFeatureEngineering:
    """Tests for feature engineering functions."""
    
    def test_calculate_returns(self, sample_ohlcv_data):
        """Test that returns are calculated correctly."""
        df = calculate_returns(sample_ohlcv_data)
        
        # Check columns exist
        assert 'ret_1m' in df.columns
        assert 'ret_5m' in df.columns
        assert 'ret_15m' in df.columns
        
        # Check values are reasonable
        assert df['ret_1m'].dropna().abs().max() < 0.1  # Max 10% per minute is reasonable
    
    def test_calculate_volatility(self, sample_ohlcv_data):
        """Test volatility calculation."""
        df = calculate_returns(sample_ohlcv_data)
        df = calculate_volatility(df)
        
        # Check columns exist
        assert 'range_5m' in df.columns
        assert 'range_15m' in df.columns
        
        # Volatility should be positive
        assert (df['range_5m'].dropna() >= 0).all()
    
    def test_calculate_technical_indicators(self, sample_ohlcv_data):
        """Test RSI and EMA calculation."""
        df = calculate_technical_indicators(sample_ohlcv_data)
        
        # Check RSI columns
        assert 'rsi_14' in df.columns
        
        # RSI should be between 0 and 100
        rsi_values = df['rsi_14'].dropna()
        assert (rsi_values >= 0).all()
        assert (rsi_values <= 100).all()
    
    def test_get_feature_columns(self):
        """Test that feature columns list is not empty."""
        columns = get_feature_columns()
        
        assert isinstance(columns, list)
        assert len(columns) > 0
        assert 'ret_1m' in columns


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_dataframe(self):
        """Test handling of empty dataframe."""
        df = pd.DataFrame()
        with pytest.raises(Exception):
            calculate_returns(df)
    
    def test_missing_columns(self):
        """Test handling of missing required columns."""
        df = pd.DataFrame({'timestamp': [1, 2, 3]})
        with pytest.raises(Exception):
            calculate_returns(df)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
