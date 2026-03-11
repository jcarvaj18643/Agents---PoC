from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.config import settings


class LLMClientFactory:
    def build(self) -> ChatOpenAI:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not configured.")

        return ChatOpenAI(
            model=settings.openai_model,
            temperature=0,
            api_key=settings.openai_api_key,
        )
