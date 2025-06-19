import json
import os
import requests
from langchain.tools import tool
from dotenv import load_dotenv
from pathlib import Path

#Import so that the StockDataTool can inherit from the base class 
from crewai.tools import BaseTool


# Load .env from project root (3 levels up from this file)
env_path = Path(__file__).resolve().parents[3] / '.env'
load_dotenv(dotenv_path=env_path)

# I can also use a class and not have any member functions because with langchain tools it gets depreciated
# Right now I am using the class so I can import the class from the crew.py becuase Idk if this will have somehting wrong 

#class AlphaVantageTool(): 
@tool("Fetch the daily S&P data")
def get_daily_stock_data(symbol):
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


class StockDataTool(BaseTool):
    name: str = "get_daily_stock_data"
    description: str = "Fetch daily OHLC data for a given stock symbol using Alpha Vantage API."

    def _run(self, symbol: str) -> str:
        try:
            return get_daily_stock_data(symbol)
        except Exception as e:
            return f"Error fetching stock data: {str(e)}"