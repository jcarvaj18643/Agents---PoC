from __future__ import annotations

import logging

from app.services.signal_extraction_service import SignalExtractionService
from app.state import AgentState


logger = logging.getLogger(__name__)


def run(state: AgentState, service: SignalExtractionService) -> AgentState:
    logger.info("node=extract_signals start")

    extracted = service.extract(
        market_data=state.get("market_data", {}),
        macro_data=state.get("macro_data", {}),
        news_items=state.get("raw_news", []),
    )

    logger.info("node=extract_signals done count=%s", len(extracted))

    return {"extracted_signals": extracted, "error": None}
