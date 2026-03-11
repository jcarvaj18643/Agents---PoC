from __future__ import annotations


class RelevanceService:
    INCLUDE = (
        "usd/cop",
        "usd cop",
        "usd",
        "dollar",
        "peso",
        "cop",
        "colombia",
        "banrep",
        "fed",
        "inflation",
        "oil",
        "brent",
        "wti",
        "opec",
        "dxy",
        "treasury",
        "yield",
        "vix",
        "emfx",
        "emerging market",
        "rates",
        "risk",
    )

    def filter_relevant_news(self, news_items: list[dict[str, str]]) -> list[dict[str, str]]:
        relevant: list[dict[str, str]] = []
        for item in news_items:
            text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
            if any(token in text for token in self.INCLUDE):
                relevant.append(item)

        if not relevant:
            return news_items
        return relevant
