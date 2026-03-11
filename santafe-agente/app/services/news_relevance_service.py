from typing import List
from app.domain.news_models import NewsItem


class NewsRelevanceService:
    def filter_relevant_news(self, news_items: List[NewsItem]) -> List[NewsItem]:
        if not news_items:
            return []

        include_tokens = (
            "independiente santa fe",
            "santa fe",
            "cardenal",
            "leon",
            "fpc",
            "liga betplay",
        )
        exclude_tokens = (
            "new mexico",
            "santa fe, argentina",
            "provincia de santa fe",
        )

        relevant_items: List[NewsItem] = []

        for item in news_items:
            text = f"{item.get('title', '')} {item.get('summary', '')}".lower()

            if any(token in text for token in exclude_tokens):
                continue

            if any(token in text for token in include_tokens):
                relevant_items.append(item)

        # Safe fallback: if heuristic filtering is too strict, keep original items.
        if not relevant_items:
            return news_items

        return relevant_items
 