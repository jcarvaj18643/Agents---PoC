from typing import List
from langchain_core.messages import HumanMessage, SystemMessage

from app.clients.llm_client import build_llm_client
from app.domain.news_models import NewsItem


class NewsRankingService:
    def rank_news(self, news_items: List[NewsItem], top_k: int = 4) -> List[NewsItem]:
        if not news_items:
            return []

        llm = build_llm_client()

        scored_items = []

        for item in news_items:
            prompt = (
                "Score this news item for inclusion in a short summary about the current state "
                "of Independiente Santa Fe, the Colombian football club.\n\n"
                f"Title: {item['title']}\n"
                f"Source: {item['source']}\n"
                f"Published: {item['published']}\n"
                f"Summary: {item['summary']}\n\n"
                "Scoring rules:\n"
                "- 5 = highly important current club news (transfers, official statements, match impact, controversy, injuries, tactical or squad updates)\n"
                "- 4 = clearly relevant club news\n"
                "- 3 = somewhat relevant context\n"
                "- 2 = weak relevance\n"
                "- 1 = barely useful\n\n"
                "Return only one integer from 1 to 5."
            )

            response = llm.invoke([
                SystemMessage(
                    content=(
                        "You are a strict sports news ranking system. "
                        "Return only one integer between 1 and 5."
                    )
                ),
                HumanMessage(content=prompt),
            ])

            raw_score = str(response.content).strip()
            normalized_score = raw_score.replace(".", "").strip()

            try:
                score = int(normalized_score)
            except ValueError:
                score = 1

            scored_items.append((score, item))

        scored_items.sort(key=lambda x: x[0], reverse=True)

        ranked_items = [item for score, item in scored_items[:top_k]]
        return ranked_items