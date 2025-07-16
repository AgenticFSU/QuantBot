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
    symbol: Union[str, List[str]] = Field(
        ..., description="A single stock symbol or a list of symbols like ['AAPL', 'MSFT']"
    )
    interval: str = Field(
        'daily',
        description="Time interval for OHLC data: 'daily', 'weekly', or 'monthly'. Default is 'daily'. Ignored if current=True."
    )
    current: bool = Field(
        False,
        description="Set to true to fetch only the most recent price (using intraday data). Default is false."
    )


#PROBLEM: There is a limit of 75 calls per minute in av api and also when we feed a lot of info to the AI it breaks, it says that there is a lot of input 
class FetchStockSummaryTool(BaseTool):
    name: str = "fetch_stock_summary"
    description: str = (
        "Fetches stock data for given ticker(s). "
        "Supports daily, weekly, monthly OHLC data (5 periods), returns, and RSI (only on daily). "
        "Set current=True to fetch just the most recent price. "
        "Example: {\"symbol\": \"AAPL\", \"interval\": \"weekly\", \"current\": false}"
    )
    args_schema: Type[StockInput] = StockInput

    def fetch_single_stock(self, symbol: str, api_key: str, interval: str = 'daily') -> dict:
        """
        Fetch data for a single stock symbol, including RSI and returns.
        interval: 'daily', 'weekly', or 'monthly'
        """
        logger.info(f"Fetching stock data for symbol: {symbol} at {interval} interval")

        # map user-friendly interval to API function & JSON keys
        interval_map = {
            'daily': ('TIME_SERIES_DAILY', 'Time Series (Daily)'),
            'weekly': ('TIME_SERIES_WEEKLY', 'Weekly Time Series'),
            'monthly': ('TIME_SERIES_MONTHLY', 'Monthly Time Series')
        }

        if interval not in interval_map:
            raise ValueError(f"Invalid interval '{interval}'. Choose from: daily, weekly, monthly")

        function_name, json_key = interval_map[interval]

        url = "https://www.alphavantage.co/query"
        params = {
            "function": function_name,
            "symbol": symbol,
            "outputsize": "compact",
            "apikey": api_key
        }

        try:
            response = requests.get(url, params=params)
            data = response.json()

            if json_key not in data:
                error_msg = f"Error fetching data for {symbol}: {data.get('Note') or data.get('Error Message') or data}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            series_data = data[json_key]
            latest_5_periods = dict(list(series_data.items())[:5])

                
                #Formatting the data for the output
            formatted_data = {
                    "symbol": symbol,
                    "last_updated": list(latest_5_periods.keys())[0] if latest_5_periods else None,   
                    "daily_data": {},
                    "daily_returns": {},
                }

            prev_close = None
            for date, values in latest_5_periods.items():
                close_price = float(values["4. close"])
                formatted_data["daily_data"][date] = {
                    "open": float(values["1. open"]),
                    "high": float(values["2. high"]),
                    "low": float(values["3. low"]),
                    "close": close_price,
                    "volume": int(values["5. volume"])
                }
                if prev_close:
                    daily_return = (close_price - prev_close) / prev_close
                    formatted_data["daily_returns"][date] = round(daily_return, 4)
                prev_close = close_price

            # Fetch RSI
            rsi_params = {
                "function": "RSI",
                "symbol": symbol,
                "interval": "daily",
                "time_period": 14,
                "series_type": "close",
                "apikey": api_key
            }

            rsi_resp = requests.get(url, params=rsi_params)
            rsi_data = rsi_resp.json()
            rsi_values = rsi_data.get("Technical Analysis: RSI", {})
            if rsi_values:
                # Get most recent RSI value
                recent_date, recent_rsi = next(iter(rsi_values.items()))
                formatted_data["rsi"] = {recent_date: float(recent_rsi["RSI"])}
            else:
                logger.warning(f"No RSI data for {symbol}")

            logger.info(f"Successfully fetched data for {symbol}")
            return formatted_data

        except Exception as e:
            logger.error(f"Request error for {symbol}: {str(e)}")
            return None
        

    def fetch_current_price(self, symbol: str, api_key: str, interval: str = '1min') -> dict:
        """
        Fetch the most recent stock price using intraday data.
        """
        logger.info(f"Fetching current price for {symbol} with {interval} interval")

        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_INTRADAY",
            "symbol": symbol,
            "interval": interval,
            "outputsize": "compact",
            "apikey": api_key
        }

        try:
            response = requests.get(url, params=params)
            data = response.json()

            time_series_key = f"Time Series ({interval})"
            if time_series_key not in data:
                error_msg = f"Error fetching intraday data for {symbol}: {data.get('Note') or data.get('Error Message') or data}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            series_data = data[time_series_key]

            # Get the most recent timestamp and price
            most_recent_timestamp = sorted(series_data.keys())[0]
            most_recent_data = series_data[most_recent_timestamp]
            current_price = float(most_recent_data["4. close"])

            result = {
                "symbol": symbol,
                "timestamp": most_recent_timestamp,
                "current_price": current_price,
                "ohlc": {
                    "open": float(most_recent_data["1. open"]),
                    "high": float(most_recent_data["2. high"]),
                    "low": float(most_recent_data["3. low"]),
                    "close": current_price,
                    "volume": int(most_recent_data["5. volume"])
                }
            }

            logger.info(f"Current price for {symbol}: {current_price} at {most_recent_timestamp}")
            return result

        except Exception as e:
            logger.error(f"Error fetching current price for {symbol}: {str(e)}")
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


    def _run(self, symbol: Union[str, List[str]], interval: str = 'daily', current: bool = False) -> str:

        """
        Run the tool.
        Pass `current=True` to fetch current price instead of OHLC.
        """
        api_key = os.environ['ALPHA_VANTAGE_API_KEY']

        try:
            symbols = [symbol] if isinstance(symbol, str) else symbol

            if current:
                result = {}
                for sym in symbols:
                    res = self.fetch_current_price(sym, api_key)
                    if res:
                        result[sym] = res
                return json.dumps(result, indent=2)

            else:
                result = self.return_all_stock_data(symbols)
                return json.dumps(result, indent=2)

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logger.error(error_msg)
            return error_msg


#Test it locally in the file
if __name__ == "__main__":
    data = FetchStockSummaryTool().return_all_stock_data() # Empty input for no-arg function
    print(json.dumps(data, indent=2))
