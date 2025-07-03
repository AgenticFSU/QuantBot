import os
import sys
import json
import requests
import feedparser
from crewai.tools import BaseTool
from crewai import Agent, Task
from unstructured.partition.html import partition_html
from langchain_community.llms import Ollama


TRUSTED_DOMAINS = [
    "reuters.com", "bloomberg.com", "cnbc.com", "marketwatch.com",
    "finance.yahoo.com", "wsj.com", "seekingalpha.com", "investopedia.com"
]
EXCLUDED_DOMAINS = ["youtube.com", "pinterest.com", "facebook.com"]

class NewsImpactTool(BaseTool):
    name: str = "get_stock_news_impact"
    description: str = "parse news articles, extract key information, and generate concise summaries."

    
    def search_rss_articles(self, symbol: str, max_results: int = 5):
        query = f"{symbol} stock"
        rss_url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(rss_url)

        all_links = []
        for entry in feed.entries:
            link = entry.link
            all_links.append(link)
            if len(all_links) >= max_results:
                break

        return all_links
    
    def summarize_article(self, url: str) -> str:

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; StockAnalyzerBot/1.0; +http://yourdomain.com)"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        import time
        time.sleep(1)  # 1 second between article fetches


        elements = partition_html(text=response.text)
        filtered_elements = [
            str(el) for el in elements
            if not str(el).strip().lower().startswith(('cookie', 'accept', 'terms', 'footer', 'privacy'))
        ]
        full_text = "\n\n".join(filtered_elements)
        chunks = [full_text[i:i + 8000] for i in range(0, len(full_text), 8000)]

        summaries = []
        for chunk in chunks:
            agent = Agent(
                role='Financial News Analyst',
                goal='Analyze news and determine stock impact.',
                backstory="You are a financial analyst tasked with evaluating news.",
                llm=Ollama(model=os.getenv('MODEL', 'llama3')),
                allow_delegation=False
            )

            task = Task(
                agent=agent,
                description=f"""
Analyze the following news content. Summarize the article and rate your confidence from 1 to 10 that the stock will go up (10) or down (1), with 5 meaning no change.

You must provide:
- A short summary.
- A confidence score from 1 to 10.
- A brief justification.

CONTENT:
----------
{chunk}
"""
            )
            result = task.execute()
            summaries.append(result)

        return "\n\n".join(summaries)

    def _run(self, symbol: str) -> str:
        try:
            articles = self.search_rss_articles(symbol)
            if not articles:
                return json.dumps({"symbol": symbol, "error": "No trusted articles found."})

            summary = self.summarize_article(articles[0])
            return json.dumps({
                "symbol": symbol,
                "source": articles[0],
                "summary_analysis": summary
            }, indent=2)

        except Exception as e:
            return json.dumps({"symbol": symbol, "error": str(e)})

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python news_scraper_tool.py <TICKER>")
        sys.exit(1)

    symbol = sys.argv[1]
    tool = NewsImpactTool()
    output = tool._run(symbol)
    print(output)
