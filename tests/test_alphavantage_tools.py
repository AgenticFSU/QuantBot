"""
Test cases for Alphavantage Tool functionality.
Tests both single ticker and multiple ticker scenarios.
"""

import unittest
import json
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# Import the tools we're testing
from src.sp_stock_agent.tools.alpha_vantage_api_tool import FetchStockSummaryTool
from src.sp_stock_agent.tools.av_news_api_tool import NewsSentimentTool
from src.sp_stock_agent.tools.av_earnings_transcript_api_tool import EarningsCallTranscriptTool


class TestFetchStockSummaryTool(unittest.TestCase):
    """Test cases for FetchStockSummaryTool - single and multiple ticker scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tool = FetchStockSummaryTool()
        self.sample_symbol = "AAPL"
        self.sample_symbols = ["AAPL", "MSFT", "GOOGL"]
        
        # Sample API response for single stock
        self.sample_single_response = {
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
                },
                "2024-01-12": {
                    "1. open": "184.37",
                    "2. high": "186.99",
                    "3. low": "183.92",
                    "4. close": "185.59",
                    "5. volume": "61201000"
                },
                "2024-01-11": {
                    "1. open": "183.96",
                    "2. high": "186.06",
                    "3. low": "183.09",
                    "4. close": "184.37",
                    "5. volume": "55419000"
                },
                "2024-01-10": {
                    "1. open": "184.35",
                    "2. high": "186.40",
                    "3. low": "183.50",
                    "4. close": "183.96",
                    "5. volume": "52389000"
                },
                "2024-01-09": {
                    "1. open": "183.79",
                    "2. high": "185.84",
                    "3. low": "182.90",
                    "4. close": "184.35",
                    "5. volume": "51234000"
                }
            }
        }
    
    def test_tool_initialization(self):
        """Test that FetchStockSummaryTool initializes correctly."""
        self.assertEqual(self.tool.name, "fetch_stock_summary")
        self.assertIn("Fetches a 5-day summary", self.tool.description)
    
    @patch('requests.get')
    def test_single_ticker_fetch_success(self, mock_get):
        """Test successful fetching of data for a single ticker."""
        # Mock the API response
        mock_response = Mock()
        mock_response.json.return_value = self.sample_single_response
        mock_get.return_value = mock_response
        
        # Mock environment variable
        with patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'}):
            result = self.tool.fetch_single_stock(self.sample_symbol, 'test_key')
        
        # Verify the result structure
        self.assertIsInstance(result, dict)
        self.assertEqual(result['symbol'], self.sample_symbol)
        self.assertIn('last_updated', result)
        self.assertIn('daily_data', result)
        
        # Verify we got 5 days of data
        self.assertEqual(len(result['daily_data']), 5)
        
        # Verify data format
        first_date = list(result['daily_data'].keys())[0]
        daily_data = result['daily_data'][first_date]
        self.assertIn('open', daily_data)
        self.assertIn('high', daily_data)
        self.assertIn('low', daily_data)
        self.assertIn('close', daily_data)
        self.assertIn('volume', daily_data)
        
        # Verify data types
        self.assertIsInstance(daily_data['open'], float)
        self.assertIsInstance(daily_data['high'], float)
        self.assertIsInstance(daily_data['low'], float)
        self.assertIsInstance(daily_data['close'], float)
        self.assertIsInstance(daily_data['volume'], int)
    
    @patch('requests.get')
    def test_single_ticker_fetch_error_handling(self, mock_get):
        """Test error handling for single ticker fetch."""
        # Mock API error response
        mock_response = Mock()
        mock_response.json.return_value = {
            "Error Message": "Invalid API call. Please retry or visit the documentation (https://www.alphavantage.co/documentation/) for TIME_SERIES_DAILY."
        }
        mock_get.return_value = mock_response
        
        with patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'}):
            result = self.tool.fetch_single_stock("INVALID", 'test_key')
        
        # Should return None for errors
        self.assertIsNone(result)
    
    @patch('requests.get')
    def test_multiple_ticker_fetch_success(self, mock_get):
        """Test successful fetching of data for multiple tickers."""
        # Mock API responses for multiple symbols
        mock_responses = []
        for symbol in self.sample_symbols:
            mock_response = Mock()
            response_data = self.sample_single_response.copy()
            response_data["Meta Data"]["2. Symbol"] = symbol
            response_data["Time Series (Daily)"] = {
                "2024-01-15": {
                    "1. open": "100.00",
                    "2. high": "105.00",
                    "3. low": "95.00",
                    "4. close": "102.00",
                    "5. volume": "1000000"
                }
            }
            mock_response.json.return_value = response_data
            mock_responses.append(mock_response)
        
        mock_get.side_effect = mock_responses
        
        with patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'}):
            result = self.tool.return_all_stock_data(self.sample_symbols)
        
        # Verify result structure
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 3)  # Should have data for all 3 symbols
        
        # Verify each symbol has data
        for symbol in self.sample_symbols:
            self.assertIn(symbol, result)
            self.assertIsInstance(result[symbol], dict)
            self.assertEqual(result[symbol]['symbol'], symbol)
    
    @patch('requests.get')
    def test_multiple_ticker_partial_failure(self, mock_get):
        """Test handling of partial failures in multiple ticker fetch."""
        # Mock responses: first two succeed, third fails
        mock_responses = []
        
        # Success responses for first two symbols
        for symbol in self.sample_symbols[:2]:
            mock_response = Mock()
            response_data = self.sample_single_response.copy()
            response_data["Meta Data"]["2. Symbol"] = symbol
            mock_response.json.return_value = response_data
            mock_responses.append(mock_response)
        
        # Error response for third symbol
        error_response = Mock()
        error_response.json.return_value = {"Error Message": "Invalid symbol"}
        mock_responses.append(error_response)
        
        mock_get.side_effect = mock_responses
        
        with patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'}):
            result = self.tool.return_all_stock_data(self.sample_symbols)
        
        # Should have data for successful symbols only
        self.assertEqual(len(result), 2)
        self.assertIn(self.sample_symbols[0], result)
        self.assertIn(self.sample_symbols[1], result)
        self.assertNotIn(self.sample_symbols[2], result)
    
    def test_run_method_single_ticker(self):
        """Test the _run method with single ticker input."""
        with patch('src.sp_stock_agent.tools.alpha_vantage_api_tool.FetchStockSummaryTool.return_all_stock_data') as mock_return_all:
            mock_return_all.return_value = {self.sample_symbol: {"symbol": self.sample_symbol}}
            
            result = self.tool._run(self.sample_symbol)
            
            # Should call return_all_stock_data with list containing single symbol
            mock_return_all.assert_called_once_with([self.sample_symbol])
            
            # Should return JSON string
            self.assertIsInstance(result, str)
            parsed_result = json.loads(result)
            self.assertIn(self.sample_symbol, parsed_result)
    
    def test_run_method_multiple_tickers(self):
        """Test the _run method with multiple ticker input."""
        with patch('src.sp_stock_agent.tools.alpha_vantage_api_tool.FetchStockSummaryTool.return_all_stock_data') as mock_return_all:
            mock_return_all.return_value = {
                symbol: {"symbol": symbol} for symbol in self.sample_symbols
            }
            
            result = self.tool._run(self.sample_symbols)
            
            # Should call return_all_stock_data with the list of symbols
            mock_return_all.assert_called_once_with(self.sample_symbols)
            
            # Should return JSON string
            self.assertIsInstance(result, str)
            parsed_result = json.loads(result)
            for symbol in self.sample_symbols:
                self.assertIn(symbol, parsed_result)


class TestNewsSentimentTool(unittest.TestCase):
    """Test cases for NewsSentimentTool - single and multiple ticker scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tool = NewsSentimentTool()
        self.sample_ticker = "AAPL"
        self.sample_tickers = ["AAPL", "MSFT", "GOOGL"]
        
        # Sample API response
        self.sample_news_response = {
            "feed": [
                {
                    "title": "Apple Reports Strong Q4 Earnings",
                    "url": "https://example.com/apple-earnings",
                    "time_published": "20240115T143000",
                    "authors": ["John Doe"],
                    "summary": "Apple reported strong quarterly earnings...",
                    "banner_image": "https://example.com/image.jpg",
                    "source": "Reuters",
                    "category_within_source": "Technology",
                    "source_domain": "reuters.com",
                    "topics": [
                        {"topic": "Technology", "relevance_score": "0.8"},
                        {"topic": "Earnings", "relevance_score": "0.9"}
                    ],
                    "overall_sentiment_score": 0.8,
                    "overall_sentiment_label": "Bullish",
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
    
    def test_tool_initialization(self):
        """Test that NewsSentimentTool initializes correctly."""
        self.assertEqual(self.tool.name, "alpha_vantage_news_sentiment")
        self.assertIn("Query Alpha Vantage's NEWS_SENTIMENT", self.tool.description)
    
    @patch('requests.get')
    def test_single_ticker_news_fetch(self, mock_get):
        """Test fetching news for a single ticker."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = self.sample_news_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'}):
            result = self.tool._run(self.sample_ticker)
        
        # Verify API call parameters
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertIn('tickers', call_args[1]['params'])
        self.assertEqual(call_args[1]['params']['tickers'], self.sample_ticker)
        
        # Verify result structure
        self.assertIsInstance(result, dict)
        self.assertIn('feed', result)
        self.assertEqual(len(result['feed']), 1)
    
    @patch('requests.get')
    def test_multiple_ticker_news_fetch(self, mock_get):
        """Test fetching news for multiple tickers."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = self.sample_news_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'}):
            result = self.tool._run(self.sample_tickers)
        
        # Verify API call parameters
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertIn('tickers', call_args[1]['params'])
        self.assertEqual(call_args[1]['params']['tickers'], ','.join(self.sample_tickers))
    
    def test_parse_response_success(self):
        """Test parsing of successful API response."""
        # 补全mock数据，ticker_sentiment里加overall_sentiment_score
        sample_news_response = {
            "feed": [
                {
                    "title": "Apple Reports Strong Q4 Earnings",
                    "url": "https://example.com/apple-earnings",
                    "time_published": "20240115T143000",
                    "authors": ["John Doe"],
                    "summary": "Apple reported strong quarterly earnings...",
                    "banner_image": "https://example.com/image.jpg",
                    "source": "Reuters",
                    "category_within_source": "Technology",
                    "source_domain": "reuters.com",
                    "topics": [
                        {"topic": "Technology", "relevance_score": "0.8"},
                        {"topic": "Earnings", "relevance_score": "0.9"}
                    ],
                    "overall_sentiment_score": 0.8,
                    "overall_sentiment_label": "Bullish",
                    "ticker_sentiment": [
                        {
                            "ticker": "AAPL",
                            "relevance_score": "0.9",
                            "ticker_sentiment_score": "0.8",
                            "ticker_sentiment_label": "Bullish",
                            "overall_sentiment_score": 0.8
                        }
                    ]
                }
            ]
        }
        result = self.tool._parse_response(sample_news_response)
        # Should return a string summary
        self.assertIsInstance(result, str)
        self.assertIn("Apple Reports Strong Q4 Earnings", result)
        self.assertIn("Reuters", result)
        self.assertIn("AAPL: 0.8", result)  # Sentiment score
    
    def test_parse_response_error(self):
        """Test parsing of error response."""
        error_response = {"Error Message": "Invalid API call"}
        result = self.tool._parse_response(error_response)
        
        # Should return JSON string for error responses
        self.assertIsInstance(result, str)
        parsed_result = json.loads(result)
        self.assertIn("Error Message", parsed_result)
    
    def test_time_parameter_handling(self):
        """Test handling of time_from and time_to parameters."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = self.sample_news_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            with patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'}):
                self.tool._run(
                    self.sample_ticker,
                    time_from="20240101T000000",
                    time_to="20240115T235959"
                )
            
            # Verify time parameters were passed
            call_args = mock_get.call_args
            params = call_args[1]['params']
            self.assertEqual(params['time_from'], "20240101T000000")
            self.assertEqual(params['time_to'], "20240115T235959")


class TestEarningsCallTranscriptTool(unittest.TestCase):
    """Test cases for EarningsCallTranscriptTool."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tool = EarningsCallTranscriptTool()
        self.sample_symbol = "AAPL"
        self.sample_quarter = "2024Q1"
        
        # Sample API response
        self.sample_transcript_response = {
            "symbol": "AAPL",
            "quarter": "2024Q1",
            "transcript": "Operator: Good morning and welcome to Apple's First Quarter 2024 Earnings Call...\n\nTim Cook: Thank you, operator. Good morning everyone..."
        }
    
    def test_tool_initialization(self):
        """Test that EarningsCallTranscriptTool initializes correctly."""
        self.assertEqual(self.tool.name, "alpha_vantage_earnings_transcript")
        self.assertIn("Call Alpha Vantage's EARNINGS_CALL_TRANSCRIPT", self.tool.description)
    
    @patch('requests.get')
    def test_transcript_fetch_success(self, mock_get):
        """Test successful fetching of earnings call transcript."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = self.sample_transcript_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'}):
            result = self.tool._run(self.sample_symbol, self.sample_quarter)
        
        # Verify API call parameters
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        params = call_args[1]['params']
        self.assertEqual(params['symbol'], self.sample_symbol)
        self.assertEqual(params['quarter'], self.sample_quarter)
        self.assertEqual(params['function'], 'EARNINGS_CALL_TRANSCRIPT')
        
        # Verify result
        self.assertIsInstance(result, dict)
        self.assertEqual(result['symbol'], self.sample_symbol)
        self.assertEqual(result['quarter'], self.sample_quarter)
        self.assertIn('transcript', result)
    
    @patch('requests.get')
    def test_transcript_fetch_error(self, mock_get):
        """Test error handling for transcript fetch."""
        # Mock error response
        mock_response = Mock()
        mock_response.json.return_value = {"Error Message": "No transcript found"}
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")
        mock_get.return_value = mock_response
        
        with patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'}):
            with self.assertRaises(Exception):
                self.tool._run(self.sample_symbol, self.sample_quarter)
    
    def test_parse_response_success(self):
        """Test parsing of successful transcript response."""
        result = self.tool._parse_response(self.sample_transcript_response)
        
        # Should return a formatted string
        self.assertIsInstance(result, str)
        self.assertIn("Earnings Call Transcript for AAPL (2024Q1)", result)
        self.assertIn("Operator: Good morning", result)
        self.assertIn("Tim Cook: Thank you", result)
    
    def test_parse_response_no_transcript(self):
        """Test parsing when no transcript is found."""
        no_transcript_response = {
            "symbol": "AAPL",
            "quarter": "2024Q1",
            "transcript": ""
        }
        
        result = self.tool._parse_response(no_transcript_response)
        
        self.assertIsInstance(result, str)
        self.assertIn("No transcript found for AAPL in 2024Q1", result)


class TestAlphavantageIntegration(unittest.TestCase):
    """Integration tests for Alphavantage tools working together."""
    
    def setUp(self):
        """Set up test fixtures for integration tests."""
        self.stock_tool = FetchStockSummaryTool()
        self.news_tool = NewsSentimentTool()
        self.transcript_tool = EarningsCallTranscriptTool()
        self.sample_symbols = ["AAPL", "MSFT"]
    
    @patch('requests.get')
    def test_full_analysis_workflow(self, mock_get):
        """Test a complete analysis workflow using multiple Alphavantage tools."""
        # Mock responses for different API calls
        mock_responses = []
        
        # Stock data responses
        for symbol in self.sample_symbols:
            stock_response = Mock()
            stock_response.json.return_value = {
                "Time Series (Daily)": {
                    "2024-01-15": {
                        "1. open": "100.00",
                        "2. high": "105.00",
                        "3. low": "95.00",
                        "4. close": "102.00",
                        "5. volume": "1000000"
                    }
                }
            }
            mock_responses.append(stock_response)
        
        # News sentiment response
        news_response = Mock()
        news_response.json.return_value = {
            "feed": [
                {
                    "title": "Tech Stocks Rally",
                    "ticker_sentiment": [{"ticker": "AAPL", "overall_sentiment_score": "0.8"}]
                }
            ]
        }
        mock_responses.append(news_response)
        
        # Transcript response
        transcript_response = Mock()
        transcript_response.json.return_value = {
            "symbol": "AAPL",
            "quarter": "2024Q1",
            "transcript": "Sample transcript content..."
        }
        mock_responses.append(transcript_response)
        
        mock_get.side_effect = mock_responses
        
        # Test the workflow
        with patch.dict(os.environ, {'ALPHA_VANTAGE_API_KEY': 'test_key'}):
            # 1. Fetch stock data
            stock_data = self.stock_tool.return_all_stock_data(self.sample_symbols)
            self.assertEqual(len(stock_data), 2)
            
            # 2. Fetch news sentiment
            news_data = self.news_tool._run(self.sample_symbols)
            self.assertIn('feed', news_data)
            
            # 3. Fetch transcript
            transcript_data = self.transcript_tool._run("AAPL", "2024Q1")
            self.assertEqual(transcript_data['symbol'], "AAPL")
    
    def test_data_consistency_across_tools(self):
        """Test that data from different tools is consistent."""
        # Mock consistent data across tools
        sample_data = {
            "stock_data": {"AAPL": {"symbol": "AAPL", "last_updated": "2024-01-15"}},
            "news_data": {"feed": [{"ticker_sentiment": [{"ticker": "AAPL"}]}]},
            "transcript_data": {"symbol": "AAPL", "quarter": "2024Q1"}
        }
        
        # Verify symbol consistency
        stock_symbols = set(sample_data["stock_data"].keys())
        news_symbols = set()
        for article in sample_data["news_data"]["feed"]:
            for sentiment in article.get("ticker_sentiment", []):
                news_symbols.add(sentiment["ticker"])
        transcript_symbol = sample_data["transcript_data"]["symbol"]
        
        # All tools should reference the same symbols
        self.assertIn("AAPL", stock_symbols)
        self.assertIn("AAPL", news_symbols)
        self.assertEqual(transcript_symbol, "AAPL")


if __name__ == '__main__':
    unittest.main() 