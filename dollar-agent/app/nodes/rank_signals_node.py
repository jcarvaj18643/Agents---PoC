from __future__ import annotations

import logging

from app.services.ranking_service import RankingService
from app.state import AgentState


logger = logging.getLogger(__name__)


def run(state: AgentState, service: RankingService) -> AgentState:
    logger.info("node=rank_signals start")

    try:
        ranked = service.rank(state.get("extracted_signals", []))
        logger.info("node=rank_signals done count=%s", len(ranked))
        return {"ranked_signals": ranked, "error": None}
    except Exception as exc:
        warnings = list(state.get("warnings", []))
        warnings.append(f"Ranking failed, using unranked signals: {exc}")
        return {
            "ranked_signals": state.get("extracted_signals", []),
            "warnings": warnings,
            "error": None,
        }
