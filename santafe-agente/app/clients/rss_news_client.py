from urllib.parse import quote_plus

import feedparser


class RssNewsClient:
    def __init__(self, language: str = "es-419", country: str = "CO") -> None:
        self.language = language
        self.country = country

    def build_google_news_rss_url(self, query: str) -> str:
        encoded_query = quote_plus(query)
        return (
            "https://news.google.com/rss/search"
            f"?q={encoded_query}"
            f"&hl={self.language}"
            f"&gl={self.country}"
            f"&ceid={self.country}:{self.language}"
        )

    def search(self, query: str):
        rss_url = self.build_google_news_rss_url(query)
        return feedparser.parse(rss_url)