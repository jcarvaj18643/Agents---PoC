from typing import List

from app.clients.rss_news_client import RssNewsClient
from app.domain.news_models import NewsItem
from app.utils.text_cleaner import clean_html


class NewsSearchService:
    def __init__(self, rss_client: RssNewsClient) -> None:
        self.rss_client = rss_client

    def search_santa_fe_news(self, query: str, max_results: int = 5) -> List[NewsItem]:
        search_query = f"Independiente Santa Fe fútbol colombiano {query}".strip()
        feed = self.rss_client.search(search_query)

        results: List[NewsItem] = []

        for entry in feed.entries:
            title = entry.get("title", "")
            summary = clean_html(entry.get("summary", ""))
            combined_text = f"{title} {summary}".lower()

            if "santa fe" not in combined_text:
                continue

            news_item: NewsItem = {
                "title": title,
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "source": (
                    entry.get("source", {}).get("title", "")
                    if entry.get("source")
                    else ""
                ),
                "summary": summary,
            }
            results.append(news_item)

            if len(results) >= max_results:
                break

        return results