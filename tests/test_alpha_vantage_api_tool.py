import os
import json
import unittest
from unittest.mock import patch, MagicMock

from src.sp_stock_agent.tools.alpha_vantage_api_tool import FetchStockSummaryTool

class TestAlphaVantageAPITool(unittest.TestCase):
    def setUp(self):
        self.tool = FetchStockSummaryTool()
        self.api_key = "demo_key"
        self.single_symbol = "AAPL"
        self.multiple_symbols = ["AAPL", "MSFT"]
        self.mock_response = {
            "Time Series (Daily)": {
                "2024-07-10": {
                    "1. open": "100.0",
                    "2. high": "110.0",
                    "3. low": "99.0",
                    "4. close": "105.0",
                    "5. volume": "1000000"
                },
                "2024-07-09": {
                    "1. open": "101.0",
                    "2. high": "111.0",
                    "3. low": "98.0",
                    "4. close": "104.0",
                    "5. volume": "900000"
                },
                "2024-07-08": {
                    "1. open": "102.0",
                    "2. high": "112.0",
                    "3. low": "97.0",
                    "4. close": "103.0",
                    "5. volume": "800000"
                },
                "2024-07-07": {
                    "1. open": "103.0",
                    "2. high": "113.0",
                    "3. low": "96.0",
                    "4. close": "102.0",
                    "5. volume": "700000"
                },
                "2024-07-06": {
                    "1. open": "104.0",
                    "2. high": "114.0",
                    "3. low": "95.0",
                    "4. close": "101.0",
                    "5. volume": "600000"
                }
            }
        }

    @patch.dict(os.environ, {"ALPHA_VANTAGE_API_KEY": "demo_key"})
    @patch("src.sp_stock_agent.tools.alpha_vantage_api_tool.requests.get")
    def test_single_ticker(self, mock_get):
        mock_get.return_value.json.return_value = self.mock_response
        result_json = self.tool._run(self.single_symbol)
        result = json.loads(result_json)
        self.assertIn(self.single_symbol, result)
        self.assertIn("daily_data", result[self.single_symbol])
        self.assertEqual(len(result[self.single_symbol]["daily_data"]), 5)
        print("✅ Single ticker test passed.")

    @patch.dict(os.environ, {"ALPHA_VANTAGE_API_KEY": "demo_key"})
    @patch("src.sp_stock_agent.tools.alpha_vantage_api_tool.requests.get")
    def test_multiple_ticker(self, mock_get):
        # Each call returns the same mock response for simplicity
        mock_get.return_value.json.return_value = self.mock_response
        result_json = self.tool._run(self.multiple_symbols)
        result = json.loads(result_json)
        for symbol in self.multiple_symbols:
            self.assertIn(symbol, result)
            self.assertIn("daily_data", result[symbol])
            self.assertEqual(len(result[symbol]["daily_data"]), 5)
        print("✅ Multiple ticker test passed.")

if __name__ == "__main__":
    unittest.main() 