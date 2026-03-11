from __future__ import annotations

import logging

from app.services.macro_analysis_service import MacroAnalysisService
from app.state import AgentState


logger = logging.getLogger(__name__)


def run(state: AgentState, service: MacroAnalysisService) -> AgentState:
    logger.info("node=analyze_macro_context start")
    macro_data = service.analyze(state.get("market_data", {}))
    logger.info(
        "node=analyze_macro_context done risk_sentiment=%s",
        macro_data.get("risk_sentiment", "unknown"),
    )
    return {"macro_data": macro_data, "error": None}
