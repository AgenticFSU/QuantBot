import os
import json
import logging
import requests
from dotenv import load_dotenv

from typing import Optional, Type
from pydantic import BaseModel, Field
from datetime import datetime

from crewai.tools import BaseTool

# ------------------------------------------------------------
# 1) Logger setup: dedicated file for earnings transcripts
# ------------------------------------------------------------
os.makedirs("logs", exist_ok=True)

logger = logging.getLogger("alpha_vantage_transcript_tool")
logger.setLevel(logging.INFO)
logger.propagate = False

formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# File handler → logs/alpha_vantage_transcript_tool.log
fh = logging.FileHandler("logs/alpha_vantage_transcript_tool.log")
fh.setLevel(logging.INFO)
fh.setFormatter(formatter)
logger.addHandler(fh)

# Console handler (optional)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)
logger.addHandler(ch)


# ------------------------------------------------------------
# 2) Pydantic schema for the tool’s arguments
# ------------------------------------------------------------
class EarningsCallTranscriptInput(BaseModel):
    symbol: str = Field(
        ...,
        description="Ticker symbol, e.g. 'IBM'"
    )
    quarter: str = Field(
        ...,
        description="Fiscal quarter in YYYYQn format, e.g. '2024Q1' (supported since 2010Q1)"
    )


# ------------------------------------------------------------
# 3) CrewAI BaseTool implementation
# ------------------------------------------------------------
class EarningsCallTranscriptTool(BaseTool):
    """
    Crew AI tool to fetch an earnings call transcript from Alpha Vantage.
    """
    name: str = "alpha_vantage_earnings_transcript"
    description: str = (
        "Call Alpha Vantage's EARNINGS_CALL_TRANSCRIPT endpoint "
        "to retrieve a given quarter’s call transcript for a company."
    )
    args_schema: Type[EarningsCallTranscriptInput] = EarningsCallTranscriptInput

    def _run(
        self,
        symbol: str,
        quarter: str
    ) -> dict:
        # Load API key
        api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        if not api_key:
            logger.error("ALPHA_VANTAGE_API_KEY is not set")
            raise ValueError("Environment variable ALPHA_VANTAGE_API_KEY must be set")

        # Build query params
        params = {
            "function": "EARNINGS_CALL_TRANSCRIPT",
            "symbol": symbol,
            "quarter": quarter,
            "apikey": api_key
        }

        logger.info(f"Requesting EARNINGS_CALL_TRANSCRIPT with params: {params}")
        response = requests.get("https://www.alphavantage.co/query", params=params)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            logger.error(f"Alpha Vantage HTTP error: {e} — {response.text}")
            raise

        data = response.json()
        logger.info("Received earnings call transcript response")
        return data

    def _parse_response(self, response: dict) -> str:
        """
        Format the JSON into a human-readable transcript snippet.
        """
        # The AV endpoint returns something like:
        # {
        #   "symbol": "IBM",
        #   "quarter": "2024Q1",
        #   "transcript": "Operator: ...\nCEO: Good morning ...\nAnalyst: ...\n"
        # }
        symbol = response.get("symbol", "<unknown>")
        quarter = response.get("quarter", "<unknown>")
        transcript = response.get("transcript", "")

        if not transcript:
            return f"No transcript found for {symbol} in {quarter}."

        # Show a preview of the first few lines
        snippet = "\n".join(transcript.splitlines()[:10])
        return (
            f"Earnings Call Transcript for {symbol} ({quarter}):\n\n"
            f"{snippet}\n\n"
            f"...[{len(transcript.splitlines())} lines total]/..."
        )


# ------------------------------------------------------ m------
# 4) Quick sanity check
# ------------------------------------------------------------
if __name__ == "__main__":
    import os, json

    load_dotenv()

    tool = EarningsCallTranscriptTool()
    args = EarningsCallTranscriptInput(symbol="IBM", quarter="2025Q1")
    result = tool.run(**args.dict())
    print(json.dumps(result, indent=2))
