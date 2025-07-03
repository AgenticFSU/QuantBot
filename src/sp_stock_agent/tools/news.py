import feedparser

def search_top_articles(self, query: str, n_results: int = 5):
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(rss_url)

    trusted_links = []
    for entry in feed.entries:
        link = entry.link.replace('./articles/', 'https://news.google.com/articles/')
        if any(domain in link for domain in self.EXCLUDED_DOMAINS):
            continue
        if any(domain in link for domain in self.TRUSTED_DOMAINS):
            trusted_links.append(link)
        if len(trusted_links) >= n_results:
            break

    return trusted_links


if __name__ == "__main__":
    print(search_top_articles("tesla", 5))
