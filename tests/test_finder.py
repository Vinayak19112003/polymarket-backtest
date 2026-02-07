
import pytest
from unittest.mock import MagicMock, patch
from src.bot.market_finder import DynamicMarketFinder

@pytest.fixture
def finder():
    return DynamicMarketFinder()

def test_initialization(finder):
    assert finder.market_keywords == ['btc', 'bitcoin']
    assert finder.base_url == "https://gamma-api.polymarket.com"

@patch('src.bot.market_finder.requests.get')
def test_search_markets_mock(mock_get, finder):
    # Mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{"slug": "btc-updown-15m-123", "question": "Bitcoin Up or Down"}]
    mock_get.return_value = mock_response

    # Test
    markets = finder.search_markets(tag_id="102467")
    
    assert len(markets) == 1
    assert markets[0]['slug'] == "btc-updown-15m-123"
    
def test_filter_btc_15m(finder):
    # Valid market
    valid_market = {
        "slug": "btc-updown-15m-1770441300",
        "question": "Bitcoin Up or Down",
        "end_date_iso": "2030-01-01T00:00:00Z" # Future
    }
    
    # Invalid market (wrong slug)
    invalid_market = {
        "slug": "trump-vs-biden",
        "question": "Election",
        "end_date_iso": "2030-01-01T00:00:00Z"
    }
    
    filtered = finder.filter_btc_15m_markets([valid_market, invalid_market])
    assert len(filtered) == 1
    assert filtered[0]['slug'] == valid_market['slug']
