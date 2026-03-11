from typing import List

from langchain_core.messages import HumanMessage, SystemMessage

from app.clients.llm_client import build_llm_client
from app.domain.news_models import NewsItem


class NewsSummaryService:
    def summarize_santa_fe_news(self, news_items: List[NewsItem]) -> str:
        if not news_items:
            return "No se encontraron noticias recientes sobre Independiente Santa Fe."

        llm = build_llm_client()

        formatted_news = []
        for index, item in enumerate(news_items, start=1):
            formatted_news.append(
                f"{index}. Title: {item['title']}\n"
                f"   Source: {item['source']}\n"
                f"   Published: {item['published']}\n"
                f"   Summary: {item['summary']}\n"
                f"   Link: {item['link']}"
            )

        news_block = "\n\n".join(formatted_news)

        system_prompt = (
            "You are a sports news analyst specialized in Colombian football. "
            "Your task is to summarize recent news about Independiente Santa Fe. "
            "Focus only on the football club from Colombia. "
            "Ignore ambiguous references if they do not clearly refer to the club. "
            "Write the final answer in Spanish. "
            "Be concise, factual, and structured."
        )

        human_prompt = (
            "These are the recent news items found about Santa Fe.\n\n"
            f"{news_block}\n\n"
            "Please produce:\n"
            "1. A short general summary.\n"
            "2. A bullet list with the most important updates.\n"
            "3. A short note if there is ambiguity or low confidence in any item."
        )

        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ])

        return response.content