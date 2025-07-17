import os
import json
import logging
from typing import Type, List
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from newspaper import Article, Config
from transformers import pipeline
from crewai.tools import BaseTool
from bs4 import BeautifulSoup
import requests
from urllib.parse import quote
import time
import random
# Instead of: from pyrate_limiter import RequestRate, Duration, Limiter
from pyrate_limiter import Limiter, Rate, Duration




# Load environment variables
load_dotenv()

# Logging setup
os.makedirs("logs", exist_ok=True)
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/news_scraper_tool.log"),
        logging.StreamHandler()
    ]
)

# Configure newspaper to use custom headers (avoid 403s)
config = Config()
config.browser_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

# Pipelines
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
SENTIMENT_LABELS = ["BULLISH", "BEARISH", "NEUTRAL"]


# Define rate: 10 requests per minute
limiter = Limiter(Rate(10, Duration.MINUTE))

HEADERS = {
    "User-Agent": config.browser_user_agent
}

class WebScraperInput(BaseModel):
    tickers: List[str] = Field(..., description="List of stock tickers to analyze")
    max_articles: int = Field(3, description="Max number of articles to fetch per ticker")

class WebScraperTool(BaseTool):
    name: str = "news_scraper_tool"
    description: str = (
        "Scrapes news articles from DuckDuckGo and performs summarization and sentiment analysis."
    )
    args_schema: Type[BaseModel] = WebScraperInput

    def ddg_search(self, query: str, n_results: int = 5):
        try:
            limiter.try_acquire("ddg")
            url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
            response = requests.get(url, headers=HEADERS)
            time.sleep(random.uniform(2, 5))
            soup = BeautifulSoup(response.text, "html.parser")
            links = []
            for a in soup.select("a.result__a")[:n_results]:
                links.append({
                    "title": a.get_text(),
                    "url": a['href']
                })
            return links
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")
            return []

    def extract_text(self, url):
        try:
            article = Article(url, config=config)
            article.download()
            article.parse()
            return article.text
        except Exception as e:
            logger.warning(f"Failed to extract article text from {url}: {e}")
            return None

    def summarize(self, text):
        try:
            return summarizer(text, max_length=130, min_length=30, do_sample=False)[0]['summary_text']
        except Exception as e:
            logger.warning(f"Summarization failed: {e}")
            return None

    def classify_sentiment(self, summary):
        try:
            result = classifier(summary, SENTIMENT_LABELS)
            return {
                "label": result["labels"][0],
                "score": round(result["scores"][0], 4)
            }
        except Exception as e:
            logger.warning(f"Sentiment classification failed: {e}")
            return {"label": "NEUTRAL", "score": 0.0}

    def _run(self, tickers: List[str], max_articles: int = 3) -> str:
        all_results = []

        for ticker in tickers:
            query = f"{ticker} stock news"
            articles = self.ddg_search(query, max_articles)
            for art in articles:
                title = art.get("title")
                url = art.get("url")

                if not url:
                    logger.info(f"Skipping article without URL: {title}")
                    continue

                text = self.extract_text(url)
                if not text or len(text.strip()) < 50:
                    logger.info(f"Skipping short or empty article: {title}")
                    continue

                summary = self.summarize(text)
                if not summary:
                    continue

                sentiment = self.classify_sentiment(summary)

                logger.info(f"✓ {ticker} | {title} => {sentiment['label']}")

                all_results.append({
                    "ticker": ticker,
                    "title": title,
                    "url": url,
                    "summary": summary,
                    "sentiment": sentiment
                })

        json_path = "news_data.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2)

        return f"Saved {len(all_results)} articles across {len(tickers)} tickers to {json_path}"

# Optional CLI test
if __name__ == "__main__":
    test_tickers = ["AAPL", "MSFT", "GOOG"]
    tool = WebScraperTool()
    result = tool._run(tickers=test_tickers, max_articles=3)
    print(result)
