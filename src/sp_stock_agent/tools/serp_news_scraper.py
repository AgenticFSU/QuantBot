import os
import time
import random
from serpapi import GoogleSearch
from dotenv import load_dotenv
load_dotenv()



API_KEY = os.environ["SERPAPI_API_KEY"]
if not API_KEY:
    raise EnvironmentError("Missing SERPAPI_API_KEY")

def fetch_google_news(keyword, count=10, country="us", lang="en", delay_range=(0.5,1.5)):
    """Fetch news results from SerpApi's Google News API."""
    time.sleep(random.uniform(*delay_range))
    search = GoogleSearch({
        "api_key": API_KEY,
        "engine": "google_news",
        "q": keyword,
        "gl": country,
        "hl": lang,
        "no_cache": "true"
    })
    resp = search.get_dict()
    results = resp.get("news_results", [])
    return [{
        "title": a.get("title"),
        "url": a.get("link"),
        "summary": a.get("snippet"),
        "publish_date": a.get("date"),
        "source": a.get("source"),
        "thumbnail": a.get("thumbnail")
    } for a in results[:count]]

if __name__ == "__main__":
    keyword = "Nvidia AI"
    print(f"\n🔍 Searching SerpApi Google News for: {keyword}")
    for art in fetch_google_news(keyword):
        print(f"- {art['publish_date'][:10] if art['publish_date'] else 'Unknown'} | {art['source']}: {art['title']}")
        print(f"  {art['url']}")
