import os
import json
import logging
import requests
from dotenv import load_dotenv

from typing import Union, List, Optional, Type
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

# Import so that our tool can inherit from the Crew AI base class
from crewai.tools import BaseTool

# Ensure logs directory exists BEFORE configuring logging
os.makedirs('logs', exist_ok=True)

# ensure the logs directory exists
os.makedirs("logs", exist_ok=True)

# create a named logger for just this tool
logger = logging.getLogger("alpha_vantage_news_tool")
logger.setLevel(logging.INFO)
# disable propagation so you don't double-log to the root handlers
logger.propagate = False

# file handler
fh = logging.FileHandler("logs/alpha_vantage_news_tool.log")
fh.setLevel(logging.INFO)
fh_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
fh.setFormatter(fh_formatter)
logger.addHandler(fh)

# optional: console handler too
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(fh_formatter)
logger.addHandler(ch)

class NewsSentimentInput(BaseModel):
    tickers: Union[str, List[str]] = Field(
        ...,
        description="A single ticker symbol or a list of symbols, e.g. 'AAPL' or ['AAPL','MSFT']"
    )
    topics: Optional[Union[str, List[str]]] = Field(
        None,
        description="Optional comma-separated list of topics, e.g. 'technology,earnings'"
    )
    time_from: Optional[str] = Field(
        None,
        description="Return articles published on or after this time (YYYYMMDDTHHMM). "
                    "If omitted, defaults to 24 hours ago."
    )
    time_to: Optional[str] = Field(
        None,
        description="Return articles published on or before this time (YYYYMMDDTHHMM). "
                    "If omitted, defaults to now."
    )
    sort: Optional[str] = Field(
        "LATEST",
        description="Sort order: LATEST (default), EARLIEST, or RELEVANCE"
    )
    limit: Optional[int] = Field(
        50,
        description="Max number of results to return (up to 200)"
    )

class NewsSentimentTool(BaseTool):
    """
    Crew AI tool to fetch news articles and sentiment scores from Alpha Vantage.
    Defaults to the last 24 hours if no time_from is supplied.
    """
    name: str = "alpha_vantage_news_sentiment"
    description: str = (
        "Query Alpha Vantage's NEWS_SENTIMENT endpoint for market news "
        "and sentiment data on specified tickers and topics."
    )
    args_schema: Type[NewsSentimentInput] = NewsSentimentInput

    def _run(
        self,
        tickers: Union[str, List[str]],
        topics: Optional[Union[str, List[str]]] = None,
        time_from: Optional[str] = None,
        time_to: Optional[str] = None,
        sort: str = "LATEST",
        limit: int = 50
    ) -> dict:
        # 1) Load API key
        api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        if not api_key:
            logger.error("Environment variable ALPHA_VANTAGE_API_KEY is not set.")
            raise ValueError("ALPHA_VANTAGE_API_KEY environment variable must be set to use this tool.")

        # 2) Compute defaults for time_from / time_to
        now = datetime.utcnow()
        if not time_to:
            time_to = now.strftime("%Y%m%dT%H%M")
        if not time_from:
            cutoff = now - timedelta(hours=24)
            time_from = cutoff.strftime("%Y%m%dT%H%M")

        # 3) Prepare tickers string
        tickers_param = (
            ",".join(tickers) if isinstance(tickers, (list, tuple)) else tickers
        )

        # 4) Build request parameters
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": tickers_param,
            "apikey": api_key,
            "sort": sort,
            "limit": limit,
            "time_from": time_from,
            "time_to": time_to,
        }
        if topics:
            params["topics"] = (
                ",".join(topics) if isinstance(topics, (list, tuple)) else topics
            )

        logger.info(f"Requesting NEWS_SENTIMENT with params: {params}")

        # 5) Call Alpha Vantage
        response = requests.get("https://www.alphavantage.co/query", params=params)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            logger.error(f"Alpha Vantage HTTP error: {e} — response text: {response.text}")
            raise

        data = response.json()
        logger.info("Received response from NEWS_SENTIMENT endpoint")
        return data

    def _parse_response(self, response: dict) -> str:
        """
        Convert the raw JSON into a human-readable summary.
        """
        if "feed" not in response:
            return json.dumps(response, indent=2)

        summaries = []
        for article in response["feed"]:
            symbol_list = article.get("ticker_sentiment", [])
            byline = article.get("provider", "unknown source")
            published = article.get("time_published", "unknown time")
            sentiment = ", ".join(
                f"{t['ticker']}: {t['overall_sentiment_score']}"
                for t in symbol_list
            )
            summaries.append(
                f"- [{published}] {article.get('title')} (by {byline})\n"
                f"  Sentiment: {sentiment}\n"
                f"  URL: {article.get('url')}"
            )

        return "\n\n".join(summaries)

# python3 src/sp_stock_agent/tools/av_news_api_tool.py
if __name__ == "__main__":
    # Quick sanity check: no need to supply time_from/to
    load_dotenv()
    data = NewsSentimentTool()._run(tickers=["AAPL","TSLA"])
    print(json.dumps(data, indent=2))
