from __future__ import annotations

import logging

from app.services.analysis_history_service import AnalysisHistoryService
from app.services.recommendation_service import RecommendationService
from app.state import AgentState


logger = logging.getLogger(__name__)


def _extract_decision_and_confidence(final_text: str) -> tuple[str, str]:
    decision = "unknown"
    confidence = "unknown"
    for line in final_text.splitlines():
        normalized = line.strip().lower()
        if normalized.startswith("- decision:"):
            decision = line.split(":", 1)[1].strip()
        if normalized.startswith("- confianza:") or normalized.startswith("- confidence:"):
            confidence = line.split(":", 1)[1].strip()
    return decision, confidence


def run(
    state: AgentState,
    service: RecommendationService,
    analysis_history_service: AnalysisHistoryService,
) -> AgentState:
    logger.info("node=build_recommendation start")

    assumptions = list(state.get("assumptions", []))
    trend_note = analysis_history_service.build_trend_note(state.get("output_language", "spanish"))
    history_used = 0
    if trend_note:
        assumptions.append(trend_note)
        history_used = 1

    final_text = service.build_final_recommendation(
        user_query=state.get("user_query", ""),
        query_timestamp=state.get("query_timestamp", ""),
        analysis_horizon=state.get("analysis_horizon", ""),
        confidence_level=state.get("confidence_level", "low"),
        ranked_signals=state.get("ranked_signals", []),
        filtered_news=state.get("filtered_news", []),
        market_data=state.get("market_data", {}),
        scenario_analysis=state.get("scenario_analysis", {}),
        warnings=state.get("warnings", []),
        assumptions=assumptions,
        output_language=state.get("output_language", "spanish"),
    )

    decision, confidence = _extract_decision_and_confidence(final_text)
    analysis_history_service.append(
        query=state.get("user_query", ""),
        decision=decision,
        confidence=confidence,
    )

    logger.info("node=build_recommendation done")

    return {
        "final_recommendation": final_text,
        "historical_analysis_used": history_used,
        "error": None,
    }
