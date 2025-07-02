from googlesearch import search
from newspaper import Article
import time

"""I am Using the two libraries, google search that help us for 
scraping google within the results of the given url and newspaper
that help us for scraping news articles"""


def fetch_articles_with_keyword(keyword, num_results=5):

    """Smart Google query with inurl, intitle, and keyword filtering. I can also add
       onsite: and add the sites that we prefer to find"""
    
    preferred_sites = ["cnn.com"]
    site_filter = " OR ".join(f"site:{site}" for site in preferred_sites)
    search_query = f'{site_filter} intitle:{keyword}'

    results = []

    try:
        links = search(search_query, num_results=num_results)
    except Exception as e:
        print(f"Error during Google search: {e}")
        return []

    for link in links:
        if any(bad in link for bad in ["cnn-underscored", "bloomberg.com", "marketwatch.com", "yahoo.com"]):
            print(f"Skipping blocked URL: {link}")
            continue


        if keyword.lower() not in link.lower():  # filter by keyword in URL
            continue

        try:
            article = Article(link, browser_user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')
            article.download()
            article.parse()
            if keyword.lower() in article.text.lower():
                results.append({
                    'title': article.title,
                    'url': link,
                    'summary': article.summary
                })

        except Exception as e:
            print(f"Failed to process article at {link}: {e}")
    return results

if __name__ == "__main__":
    keyword = "Apple"
    num_results = 20

    articles = fetch_articles_with_keyword(keyword, num_results)

    for i, article in enumerate(articles, 1):
        print(f"\n{i}. {article['title']}")
        print(f"URL: {article['url']}")
        print(f"Summary: {article['summary'][:200]}...")
