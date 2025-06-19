import json
import os
import requests
import pandas as pd
from langchain.tools import tool
from dotenv import load_dotenv
from pathlib import Path


# Import so that the StockDataTool can inherit from the base class 
from crewai.tools import BaseTool


env_path = Path(__file__).resolve().parents[3] / '.env'
load_dotenv(dotenv_path=env_path)


# This is in case I want to get all the tickers but for now we are using the sp_500 symbols, which is a short list 
def get_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tables = pd.read_html(url)
    sp500_table = tables[0]  # The first table contains the tickers
    tickers = sp500_table["Symbol"].tolist()

    # Fix tickers like "BRK.B" to "BRK-B" (Alpha Vantage format)
    tickers = [t.replace(".", "-") for t in tickers]

    return tickers



@tool("Fetch the daily S&P data")
def get_sp500_stock_data():
    """Fetch daily OHLC data for all S&P 500 stocks, returning the latest 5 days for each symbol."""
    
    # Instead of this I could call the function get_sp500_tickers to get a list from the wikipedia but for testing purposes I will leave this one for now 
    sp500_symbols = [
        "AAPL", "MSFT", "GOOGL",
    ]
    
    api_key = os.environ['ALPHA_VANTAGE_API_KEY']
    all_stock_data = {}
    
    for symbol in sp500_symbols:
        try:
            # Fetch data for each symbol
            stock_data = fetch_single_stock_data(symbol, api_key)

            if stock_data:
                all_stock_data[symbol] = stock_data
                print(f"✓ Fetched data for {symbol}")
            else:
                print(f"✗ Failed to fetch data for {symbol}")
                
        except Exception as e:
            print(f"✗ Error fetching {symbol}: {str(e)}")
            # Continue with next symbol instead of failing completely
            continue
    
    return all_stock_data





def fetch_single_stock_data(symbol: str, api_key: str)-> dict[str, any]:

    """Fetch data for a single stock symbol."""

    url = "https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "outputsize": "compact", 
        "apikey": api_key
    }

    try:

        response = requests.get(url, params=params)
        data = response.json()

        if "Time Series (Daily)" in data:
            # get the last 5 days of trading 
            daily_data = data["Time Series (Daily)"]
            latest_5_days = dict(list(daily_data.items())[:5])
            
            #Formatting the data for the output
            formatted_data = {
                "symbol": symbol,
                "last_updated": list(latest_5_days.keys())[0] if latest_5_days else None,   
                "daily_data": {}
            }

            for date, values in latest_5_days.items():
                formatted_data["daily_data"][date] = {
                    "open": float(values["1. open"]),
                    "high": float(values["2. high"]),
                    "low": float(values["3. low"]),
                    "close": float(values["4. close"]),
                    "volume": int(values["5. volume"])
                }

            return formatted_data
    
        else:
            raise ValueError(f"Error fetching data: {data.get('Note') or data.get('Error Message') or data}")

    except Exception as e:
        print(f"Request error for {symbol}: {str(e)}")
        return None




#Test it locally in the file
if __name__ == "__main__":
    data = get_sp500_stock_data.invoke({})  # Empty input for no-arg function
    print(json.dumps(data, indent=2))




#PROBLEM: There is a limit of 75 calls per minute in av api and also when we feed a lot of info to the AI it breaks, it says that there is a lot of input 
class StockDataTool(BaseTool):
    name: str = "get_daily_stock_data"
    description: str = "Fetch daily OHLC data for a given stock symbol using Alpha Vantage API."

    def _run(self, symbol: str) -> str:
        try:
            result = get_sp500_stock_data.invoke({})
            return json.dumps(result)  # Return as JSON string
            #return get_daily_stock_data(symbol)
        except Exception as e:
            return f"Error fetching stock data: {str(e)}"
        