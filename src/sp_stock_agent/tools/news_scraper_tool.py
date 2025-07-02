import json
import os
import requests
from crewai.tools import BaseTool
from crewai import Agent, Task
from unstructured.partition.html import partition_html
from langchain.llms import Ollama

TRUSTED_DOMAINS = [
    "reuters.com", "bloomberg.com", "cnbc.com", "marketwatch.com",
    "finance.yahoo.com", "wsj.com", "seekingalpha.com", "investopedia.com"
]

EXCLUDED_DOMAINS = ["youtube.com", "pinterest.com", "facebook.com"]

class NewsImpactTool(BaseTool):
    name: str = "get_stock_news_impact"
    description: str = "parse news articles, extract key information, and generate concise summaries."

    def search_top_articles(self, query: str, n_results: int = 5):
        url = "https://google.serper.dev/search"
        payload = json.dumps({"q": query})
        headers = {
            'X-API-KEY': os.environ['SERPER_API_KEY'],
            'content-type': 'application/json'
        }
        response = requests.post(url, headers=headers, data=payload)
        results = response.json().get('organic', [])

        trusted_links = []
        for result in results:
            link = result.get("link", "")
            if any(domain in link for domain in EXCLUDED_DOMAINS):
                continue
            if any(domain in link for domain in TRUSTED_DOMAINS):
                trusted_links.append(link)
            if len(trusted_links) >= n_results:
                break

        return trusted_links

    def summarize_article(self, url: str) -> str:
        browserless_url = f"https://chrome.browserless.io/content?token={os.environ['BROWSERLESS_API_KEY']}"
        payload = json.dumps({"url": url})
        headers = {'cache-control': 'no-cache', 'content-type': 'application/json'}
        response = requests.post(browserless_url, headers=headers, data=payload)

        elements = partition_html(text=response.text)
        filtered_elements = [str(el) for el in elements if not str(el).strip().lower().startswith(('cookie', 'accept', 'terms', 'footer', 'privacy'))]
        full_text = "\n\n".join(filtered_elements)
        chunks = [full_text[i:i + 8000] for i in range(0, len(full_text), 8000)]

        summaries = []
        for chunk in chunks:
            agent = Agent(
                role='Financial News Analyst',
                goal='Analyze news and determine stock impact.',
                backstory="You are a financial analyst. Your task is to read financial news and determine whether a company's stock is likely to rise, fall, or remain stable.",
                llm=Ollama(model=os.environ['MODEL']),
                allow_delegation=False
            )

            task = Task(
                agent=agent,
                description=f"""
Analyze the following news content. Summarize the article and rate your confidence from 1 to 10 that the stock will go up (10) or down (1), with 5 meaning no significant change expected.

You must provide:
- A short summary of the news.
- A numerical confidence score from 1 to 10.
- The reasoning for that confidence score.

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
            articles = self.search_top_articles(symbol)
            if not articles:
                return json.dumps({"symbol": symbol, "error": "No trusted articles found."})

            url = articles[0]  # use first good result
            summary = self.summarize_article(url)

            return json.dumps({
                "symbol": symbol,
                "source": url,
                "summary_analysis": summary
            }, indent=2)

        except Exception as e:
            return json.dumps({"symbol": symbol, "error": str(e)})

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python news_scraper_tool.py <TICKER>")
        sys.exit(1)

    symbol = sys.argv[1]
    tool = NewsImpactTool()
    output = tool._run(symbol)
    print(output)
