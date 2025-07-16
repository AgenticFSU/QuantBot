"""
Pytest configuration and fixtures for QuantBot tests.
"""

import pytest
import os
import tempfile
import json
from unittest.mock import Mock, patch
from typing import Dict, Any


@pytest.fixture
def sample_stock_data():
    """Sample stock data for testing."""
    return {
        "AAPL": {
            "symbol": "AAPL",
            "last_updated": "2024-01-15",
            "daily_data": {
                "2024-01-15": {
                    "open": 185.59,
                    "high": 186.12,
                    "low": 183.62,
                    "close": 185.14,
                    "volume": 52489630
                },
                "2024-01-12": {
                    "open": 184.37,
                    "high": 186.99,
                    "low": 183.92,
                    "close": 185.59,
                    "volume": 61201000
                }
            }
        }
    }


@pytest.fixture
def sample_news_data():
    """Sample news data for testing."""
    return {
        "feed": [
            {
                "title": "Apple Reports Strong Q4 Earnings",
                "url": "https://example.com/apple-earnings",
                "time_published": "20240115T143000",
                "authors": ["John Doe"],
                "summary": "Apple reported strong quarterly earnings...",
                "source": "Reuters",
                "ticker_sentiment": [
                    {
                        "ticker": "AAPL",
                        "relevance_score": "0.9",
                        "ticker_sentiment_score": "0.8",
                        "ticker_sentiment_label": "Bullish"
                    }
                ]
            }
        ]
    }


@pytest.fixture
def sample_sec_table_data():
    """Sample SEC table data for testing."""
    return {
        "headers": ["Fiscal Year", "Revenue", "Operating Income", "Net Income"],
        "rows": [
            ["2021", "$365,817", "$108,949", "$94,680"],
            ["2022", "$394,328", "$119,437", "$99,803"],
            ["2023", "$383,285", "$114,301", "$96,995"]
        ]
    }


@pytest.fixture
def sample_financial_table():
    """Sample financial table for testing."""
    return {
        "headers": ["Quarter", "Revenue", "Net Income", "EPS", "Growth Rate"],
        "rows": [
            ["Q1 2024", "$100M", "$20M", "$2.00", "10%"],
            ["Q2 2024", "$110M", "$25M", "$2.50", "15%"],
            ["Q3 2024", "$120M", "$30M", "$3.00", "20%"],
            ["Q4 2024", "$130M", "$35M", "$3.50", "25%"]
        ]
    }


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    with patch.dict(os.environ, {
        'ALPHA_VANTAGE_API_KEY': 'test_key',
        'OPENAI_API_KEY': 'test_openai_key'
    }):
        yield


@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_api_responses():
    """Mock API responses for testing."""
    return {
        "stock_data": {
            "Meta Data": {
                "1. Information": "Daily Prices (open, high, low, close) and Volumes",
                "2. Symbol": "AAPL",
                "3. Last Refreshed": "2024-01-15",
                "4. Output Size": "Compact",
                "5. Time Zone": "US/Eastern"
            },
            "Time Series (Daily)": {
                "2024-01-15": {
                    "1. open": "185.59",
                    "2. high": "186.12",
                    "3. low": "183.62",
                    "4. close": "185.14",
                    "5. volume": "52489630"
                }
            }
        },
        "news_data": {
            "feed": [
                {
                    "title": "Test News Article",
                    "ticker_sentiment": [{"ticker": "AAPL", "overall_sentiment_score": "0.8"}]
                }
            ]
        },
        "transcript_data": {
            "symbol": "AAPL",
            "quarter": "2024Q1",
            "transcript": "Sample transcript content..."
        }
    }


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    return Mock(
        choices=[Mock(message=Mock(content="This is a test response from the LLM."))]
    )


def pytest_configure(config):
    """Configure pytest."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection."""
    for item in items:
        # Mark tests based on their location
        if "test_sec_parsing" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        elif "test_alphavantage_tools" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        elif "test_llm_table_integration" in item.nodeid:
            item.add_marker(pytest.mark.slow) 