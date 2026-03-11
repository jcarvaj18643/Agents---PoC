from __future__ import annotations

import logging

from app.services.news_service import NewsService
from app.state import AgentState


logger = logging.getLogger(__name__)


def run(state: AgentState, service: NewsService) -> AgentState:
    logger.info("node=fetch_news start retry_count=%s", state.get("retry_count", 0))

    broaden = state.get("retry_count", 0) > 0
    raw_news = service.fetch_news(state.get("user_query", ""), broaden=broaden)
    history_used = int(getattr(service, "last_history_used", 0))

    warnings = list(state.get("warnings", []))
    if len(raw_news) < 3:
        warnings.append("Fresh news (<= 7 days) are insufficient.")
    elif history_used > 0:
        warnings.append(f"Historical overlay used from last 5 days: {history_used} news items.")

    logger.info("node=fetch_news done items=%s broaden=%s", len(raw_news), broaden)

    return {
        "raw_news": raw_news,
        "warnings": warnings,
        "historical_news_used": history_used,
        "error": None,
    }
