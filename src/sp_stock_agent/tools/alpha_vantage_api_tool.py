import json
import os
import requests
from langchain.tools import tool
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root (3 levels up from this file)
env_path = Path(__file__).resolve().parents[3] / '.env'
load_dotenv(dotenv_path=env_path)

class AlphaVantageTool():
    @tool("Fetch the daily S&P data")
    def get_daily_stock_data(self, symbol):
        """Fetch daily OHLC data for a given stock symbol using Alpha Vantage API directly."""
        api_key = os.environ['ALPHA_VANTAGE_API_KEY']
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": "compact",  # last 100 days, use 'full' for more
            "apikey": api_key
        }
        response = requests.get(url, params=params)
        data = response.json()
        # Optional: handle errors or check if key exists
        if "Time Series (Daily)" in data:
            return data["Time Series (Daily)"]
        else:
            raise ValueError(f"Error fetching data: {data.get('Note') or data.get('Error Message') or data}")


if __name__ == "__main__":
    client = AlphaVantageTool()  
    daily_data = client.get_daily_stock_data("SPY") 
    print("First 3 days of data:")
    for date, ohlc in list(daily_data.items())[:3]:
        print(f"{date}: {ohlc}")
