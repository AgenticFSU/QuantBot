import os
import time
import random
from serpapi import GoogleSearch
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.environ["SERPAPI_API_KEY"]
if not API_KEY:
    raise EnvironmentError("Missing SERPAPI_API_KEY")

from newspaper import Article
from transformers import pipeline

# Initialize summarization pipeline (do this once)
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

def fetch_article_text(url):
    """Extract main text from a news article URL."""
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        print(f"Failed to fetch article: {e}")
        return None

def summarize_text(text, max_length=130):
    """Summarize the given text using a transformer model."""
    try:
        summary = summarizer(text, max_length=max_length, min_length=30, do_sample=False)
        return summary[0]['summary_text']
    except Exception as e:
        print(f"Failed to summarize: {e}")
        return None

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
    keyword = "Nvidia"
    output_path = "news_summaries.txt"
    print(f"\n🔍 Searching SerpApi Google News for: {keyword}")

    with open(output_path, "w", encoding="utf-8") as f:
        for art in fetch_google_news(keyword):
            title = art.get('title') or "No Title"
            url = art.get('url')
            date = art.get('publish_date')[:10] if art.get('publish_date') else 'Unknown'
            source = art.get('source')
            if url:
                full_text = fetch_article_text(url)
                if full_text and len(full_text.strip()) > 50:
                    try:
                        max_len = min(130, int(len(full_text.split()) * 0.5))
                        summary = summarize_text(full_text, max_length=max_len)
                        if summary:  # Only write if summary succeeded
                            f.write(f"- {date} | {source}: {title}\n")
                            f.write(f"  {url}\n")
                            f.write(f"  📝 Summary: {summary}\n\n")
                            print(f"- {date} | {source}: {title}")
                            print(f"  {url}")
                            print(f"  📝 Summary: {summary}\n")
                        else:
                            print(f"- {date} | {source}: {title}")
                            print(f"  {url}")
                            print("  (Summarization failed, not writing to file)\n")
                    except Exception as e:
                        print(f"- {date} | {source}: {title}")
                        print(f"  {url}")
                        print(f"  (Summarization failed: {e}, not writing to file)\n")
                else:
                    print(f"- {date} | {source}: {title}")
                    print(f"  {url}")
                    print("  (Could not fetch article text or text too short, not writing to file)\n")
            else:
                print(f"- {date} | {source}: {title}")
                print("  (No URL provided, not writing to file)\n")
    print(f"\nSummaries written to {output_path}")
