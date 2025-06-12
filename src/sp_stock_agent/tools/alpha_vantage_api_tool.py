import json
import os
import requests
from langchain.tools import tool
from dotenv import load_dotenv
from pathlib import Path

# Import so that the StockDataTool can inherit from the base class 
from crewai.tools import BaseTool


env_path = Path(__file__).resolve().parents[3] / '.env'
load_dotenv(dotenv_path=env_path)



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

    if "Time Series (Daily)" in data:

        # Get the latest 5 days only I could remove this and just return data to get all the json 
        daily_data = data["Time Series (Daily)"]
        latest_5 = dict(list(daily_data.items())[:5])
        return data["Time Series (Daily)"]

        #To return each symbol with the ticker should be return {symbol: latest_5}
        # To return latest 5
        # return data["Time Series (Daily)"] is to return the whole json recieved ["Time Series (Daily)"]
    else:
        raise ValueError(f"Error fetching data: {data.get('Note') or data.get('Error Message') or data}")


#PROBLEM: There is a limit of 75 calls per minute in av api 
class StockDataTool(BaseTool):
    name: str = "get_daily_stock_data"
    description: str = "Fetch daily OHLC data for a given stock symbol using Alpha Vantage API."

    def _run(self, symbol: str) -> str:
        try:
            result = get_daily_stock_data(symbol)
            return json.dumps(result)  # Return as JSON string
            #return get_daily_stock_data(symbol)
        except Exception as e:
            return f"Error fetching stock data: {str(e)}"