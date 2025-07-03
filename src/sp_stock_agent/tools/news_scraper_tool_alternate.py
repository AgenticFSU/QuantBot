import time
import random
from googlesearch import search
from newspaper import Article

"""Enhanced news scraper with better headers and rate limiting"""


def get_randomized_headers():
    """Generate realistic browser headers"""
    user_agents = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0'
    ]
    
    return {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    }


def fetch_articles_with_keyword(keyword, num_results=5, delay_range=(1, 2)):
    """
    Fetch articles from news sites with keyword search and date limiting
    
    Args:
        keyword: Search keyword
        num_results: Number of articles to fetch
        days_limit: Limit results to this many days (7=week, 30=month, 365=year, 0=no limit)
    """
    
    preferred_sites = ["cnn.com", "bbc.com"] # + "techcrunch.com", "theverge.com"]
    site_filter = " OR ".join(f"site:{site}" for site in preferred_sites)
    search_query = f'{site_filter} intitle:{keyword}'

    results = []

    try:
        # fetch 3x as many links as desired articles as not all of them will be successfult links 
        # Add delay before Google search to avoid rate limiting
        time.sleep(random.uniform(*delay_range))
        links = list(search(search_query, num_results=num_results*3))
        print(f"Found {len(links)} potential links")

    except Exception as e:
        print(f"Error during Google search: {e}")
        return []

    i = 0
    while i < len(links) and len(results) < num_results:
        link = links[i]
        i += 1

        # Skip unwanted domains
        blocked_domains = [
            "cnn-underscored", "bloomberg.com", "marketwatch.com", 
            "yahoo.com", "pinterest.com", "youtube.com", "twitter.com"
        ]
        if any(bad in link for bad in blocked_domains):
            print(f"Skipping blocked URL: {link}\n")
            continue

        if keyword.lower() not in link.lower():
            continue

        try:
            # Add random delay between article downloads
            time.sleep(random.uniform(*delay_range))
            
            # Get realistic headers
            headers = get_randomized_headers()
            
            # Create article with enhanced configuration
            article = Article(
                link, 
                browser_user_agent=headers['User-Agent'],
                request_timeout=10,
                ignored_content_types_defaults={
                    'application/pdf', 'application/x-pdf',
                    'application/msword', 'application/vnd.ms-excel'
                }
            )
            
            # Set additional headers for newspaper3k
            article.config.browser_user_agent = headers['User-Agent']
            article.config.request_timeout = 10
            
            print(f"Downloading article from: {link}")
            article.download()
            article.parse()
            
            # Validate article content
            if (article.text and 
                len(article.text) > 100 and 
                keyword.lower() in article.text.lower()):
                
                results.append({
                    'title': article.title or 'No title',
                    'url': link,
                    'summary': article.summary if article.summary else article.text[:300],
                    'publish_date': article.publish_date.isoformat() if article.publish_date else None,
                    'authors': article.authors or []
                })
                print(f"✅ Successfully processed: {article.title}\n")
            else:
                print(f"⚠️ Article validation failed for: {link}\n")
                
        except Exception as e:
            print(f"❌ Failed to process article at {link}: {e}\n")
            continue

    return results

if __name__ == "__main__":
    keyword = "Apple"
    num_results = 5
    
    print(f"🔍 Searching for articles about: {keyword}")
    print("=" * 60)
    
    articles = fetch_articles_with_keyword(keyword, num_results, delay_range=(1, 2))
    print(f"\n📈 FINAL RESULTS: Found {len(articles)} articles:")
    print("=" * 60)
    
    for i, article in enumerate(articles, 1):
        print(f"\n{i}. 📄 {article['title']}")
        print(f"   🌐 URL: {article['url']}")
        print(f"   ✍️  Authors: {', '.join(article['authors']) if article['authors'] else 'Unknown'}")
        print(f"   📅 Published: {article['publish_date'] or 'Unknown'}")
        print(f"   📝 Summary: {article['summary'][:200]}...")
        
    if not articles:
        print("\n⚠️  No articles found.")
