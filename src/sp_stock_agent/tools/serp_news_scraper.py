import os
import json
import logging
from typing import Type, List
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from serpapi import Client
from newspaper import Article, Config
from transformers import pipeline
from crewai.tools import BaseTool

# Load environment variables
load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_API_KEY")
if not SERPAPI_KEY:
    raise EnvironmentError("Missing SERPAPI_API_KEY")

# Logging setup
os.makedirs("logs", exist_ok=True)
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/serp_news_tool.log"),
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

# Input schema for CrewAI
class NewsScraperInput(BaseModel):
    tickers: List[str] = Field(..., description="List of stock tickers to analyze")
    max_articles: int = Field(3, description="Max number of articles to fetch per ticker")

class NewsScraperTool(BaseTool):
    name: str = "news_sentiment_analysis"
    description: str = (
        "Analyzes sentiment of financial news for selected stocks using summarization and zero-shot classification."
    )
    args_schema: Type[BaseModel] = NewsScraperInput

    def fetch_articles(self, query, max_articles):
        logger.info(f"Querying SerpApi for: {query}")
        client = Client(api_key=SERPAPI_KEY)
        results = client.search({
            "engine": "google_news",
            "q": query,
            "hl": "en",
            "gl": "us"
        })
        return results.get("news_results", [])[:max_articles]

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
            articles = self.fetch_articles(ticker, max_articles)
            for art in articles:
                title = art.get("title")
                url = art.get("link")
                source = art.get("source")
                date = art.get("date", "Unknown")

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

                logger.info(f"✓ {ticker} | {date} | {source} | {title} => {sentiment['label']}")

                all_results.append({
                    "ticker": ticker,
                    "title": title,
                    "url": url,
                    "publish_date": date,
                    "source": source,
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
    tool = NewsScraperTool()
    result = tool._run(tickers=test_tickers, max_articles=3)
    print(result)
