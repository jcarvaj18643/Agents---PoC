from typing import Dict, List, TypedDict

from app.domain.news_models import NewsItem


class AgentState(TypedDict, total=False):
    query: str
    news_results: List[NewsItem]
    filtered_news_results: List[NewsItem]
    ranked_news_results: List[NewsItem]
    final_answer: str
    error: str
    failed_node: str
    retry_counts: Dict[str, int]