from __future__ import annotations

from app.clients.news_client import NewsClient
from app.config import settings
from app.services.news_history_service import NewsHistoryService


class NewsService:
    def __init__(self, client: NewsClient) -> None:
        self.client = client
        self.history_service = NewsHistoryService()
        self.last_history_used = 0

    def _build_queries(self, user_query: str, broaden: bool = False) -> list[str]:
        base = [
            f"USD COP Colombia FX {user_query}",
            "USD COP Colombia central bank Fed oil risk sentiment",
            "Brent crude oil OPEC geopolitics impact on emerging currencies",
            "US dollar index DXY Federal Reserve rates inflation outlook",
            "VIX global risk sentiment emerging market currencies",
        ]
        if broaden:
            base.extend(
                [
                    "Colombia economy inflation BanRep peso dollar market",
                    "Latam FX flows carry trade USD strength",
                    "US Treasury yields EMFX pressure",
                ]
            )
        return base

    def fetch_news(self, user_query: str, broaden: bool = False) -> list[dict[str, str]]:
        merged: list[dict[str, str]] = []
        seen_titles: set[str] = set()

        for query in self._build_queries(user_query, broaden=broaden):
            items = self.client.search(query, max_items=settings.max_news_items)
            for item in items:
                title_key = item.get("title", "").lower()
                if title_key in seen_titles:
                    continue
                seen_titles.add(title_key)
                merged.append(item)

        global_macro_items = self.client.fetch_global_macro_news(max_items=settings.max_news_items)
        for item in global_macro_items:
            title_key = item.get("title", "").lower()
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            merged.append(item)

        with_history, used_from_history = self.history_service.merge_with_recent_history(merged)
        self.last_history_used = used_from_history
        return with_history
