from crewai.tools import BaseTool
import random

TICKERS = ["AAPL", "MSFT", "GOOG", "AMZN", "TSLA", "NVDA", "META", "NFLX", "CSCO", "INTC"]

class StockSelectorTool(BaseTool):
    name: str = "stock_selector"
    description: str = (
        "This tool gives you a list of stocks that you can analyze."
    )

    def _run(self) -> str:
        """Select the stocks that you think is worth exploring."""
        number_of_stocks = random.randint(1, 5)
        return random.sample(TICKERS, number_of_stocks)