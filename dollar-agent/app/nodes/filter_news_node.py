from __future__ import annotations

import logging

from app.services.relevance_service import RelevanceService
from app.state import AgentState


logger = logging.getLogger(__name__)


def run(state: AgentState, service: RelevanceService) -> AgentState:
    logger.info("node=filter_relevant_news start")
    filtered = service.filter_relevant_news(state.get("raw_news", []))
    logger.info("node=filter_relevant_news done count=%s", len(filtered))
    return {"filtered_news": filtered, "error": None}
