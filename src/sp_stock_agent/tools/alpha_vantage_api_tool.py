import json
import logging
import os
import requests

from typing import Union, List, Type
from pydantic import BaseModel, Field


# Import so that the FetchStockSummaryTool can inherit from the base class 
from crewai.tools import BaseTool

# Ensure logs directory exists BEFORE configuring logging
os.makedirs('logs', exist_ok=True)

# Configure logger for this module
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/alpha_vantage_tool.log'),
        logging.StreamHandler()
    ]
)

class StockInput(BaseModel):
    symbol: Union[str, List[str]] = Field(..., description="A single stock symbol or a list like ['AAPL', 'MSFT']")


#PROBLEM: There is a limit of 75 calls per minute in av api and also when we feed a lot of info to the AI it breaks, it says that there is a lot of input 
class FetchStockSummaryTool(BaseTool):
    name: str = "fetch_stock_summary"
    description: str = (
        "Fetches a 5-day summary of recent OHLC stock data for given ticker(s) "
        "(e.g. [AAPL, TSLA] or [AAPL]). "
        "Returns close price, volume, and highs/lows."
    )
    args_schema: Type[StockInput] = StockInput

    def fetch_single_stock(self, symbol: str, api_key: str) -> dict:
        """Fetch data for a single stock symbol."""
        logger.info(f"Fetching stock data for symbol: {symbol}")

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

                logger.info(f"Successfully fetched data for {symbol}")
                return formatted_data
        
            else:
                error_msg = f"Error fetching data for {symbol}: {data.get('Note') or data.get('Error Message') or data}"
                logger.error(error_msg)
                raise ValueError(error_msg)

        except Exception as e:
            logger.error(f"Request error for {symbol}: {str(e)}")
            return None


    # We dont know what will be passed if either a list or just a symbol 
    def return_all_stock_data(self, symbols):
        """Fetch and store summarized data for all passed symbols."""
        logger.info(f"Starting to fetch data for {len(symbols)} symbols: {symbols}")

        api_key = os.environ['ALPHA_VANTAGE_API_KEY']
        all_stock_data = {}
        
        for symbol in symbols:
            try:
                # Fetch data for each symbol
                stock_data = self.fetch_single_stock(symbol, api_key)

                if stock_data:
                    all_stock_data[symbol] = stock_data
                    logger.info(f"✓ Fetched data for {symbol}")
                else:
                    logger.warning(f"✗ Failed to fetch data for {symbol}")
                    
            except Exception as e:
                logger.error(f"✗ Error fetching {symbol}: {str(e)}")

                # Continue with next symbol instead of failing completely
                continue
        
        logger.info(f"Completed fetching data for {len(all_stock_data)} out of {len(symbols)} symbols")
        return all_stock_data

    def _run(self, symbol: Union[str, List[str]]) -> str:
        try:
            symbols = [symbol] if isinstance(symbol, str) else symbol
            result = self.return_all_stock_data(symbols)
            return json.dumps(result, indent=2)
        
        except Exception as e:
            error_msg = f"Error fetching stock data: {str(e)}"
            logger.error(error_msg)
            return error_msg


#Test it locally in the file
if __name__ == "__main__":
    data = FetchStockSummaryTool().return_all_stock_data() # Empty input for no-arg function
    print(json.dumps(data, indent=2))
