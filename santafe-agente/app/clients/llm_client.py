from typing import Any

from langchain_openai import ChatOpenAI

from app.config import OPENAI_MODEL


_llm_call_count = 0


def reset_llm_call_count() -> None:
    global _llm_call_count
    _llm_call_count = 0


def get_llm_call_count() -> int:
    return _llm_call_count


class CountingLLMClient:
    def __init__(self, client: ChatOpenAI) -> None:
        self._client = client

    def invoke(self, *args: Any, **kwargs: Any):
        global _llm_call_count
        _llm_call_count += 1
        return self._client.invoke(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)


def build_llm_client() -> CountingLLMClient:
    client = ChatOpenAI(
        model=OPENAI_MODEL,
        temperature=0,
    )
    return CountingLLMClient(client)