from __future__ import annotations

import logging

from app.services.fallback_service import FallbackService
from app.services.forecast_learning_service import ForecastLearningService
from app.services.validation_service import ValidationService
from app.state import AgentState


logger = logging.getLogger(__name__)


def run(
    state: AgentState,
    validation_service: ValidationService,
    fallback_service: FallbackService,
    learning_service: ForecastLearningService,
) -> AgentState:
    logger.info("node=validate_analysis start")

    result = validation_service.validate(
        market_data=state.get("market_data", {}),
        filtered_news=state.get("filtered_news", []),
        ranked_signals=state.get("ranked_signals", []),
        degraded_mode=state.get("degraded_mode", False),
    )

    adjusted_confidence, learning_note = learning_service.adjust_confidence(
        result.confidence_level
    )
    warnings = list(state.get("warnings", []))
    if learning_note:
        warnings.append(f"Learning: {learning_note}")

    updates: AgentState = {
        "validation_passed": result.is_valid,
        "validation_issues": result.issues,
        "confidence_level": adjusted_confidence,
        "warnings": warnings,
        "error": None,
    }

    if result.is_valid:
        updates["route_hint"] = "build_scenarios"
        logger.info("node=validate_analysis done status=valid")
        return updates

    if fallback_service.can_retry(state):
        retry_route = "retry_fetch_news"
        if any("Insufficient market indicators" in issue for issue in result.issues):
            retry_route = "retry_fetch_market_data"

        retry_updates = fallback_service.mark_retry(
            state,
            reason="validation_insufficient_quality",
        )
        updates.update(retry_updates)
        if learning_note:
            merged_warnings = list(updates.get("warnings", []))
            merged_warnings.append(f"Learning: {learning_note}")
            updates["warnings"] = merged_warnings
        updates["route_hint"] = retry_route
        logger.info(
            "node=validate_analysis done status=retry retry_count=%s",
            updates.get("retry_count", 0),
        )
        return updates

    degraded_updates = fallback_service.mark_degraded(
        state,
        reason="validation_failed_retries_exhausted",
    )
    updates.update(degraded_updates)
    if learning_note:
        merged_warnings = list(updates.get("warnings", []))
        merged_warnings.append(f"Learning: {learning_note}")
        updates["warnings"] = merged_warnings
    updates["route_hint"] = "build_scenarios"
    logger.info("node=validate_analysis done status=degraded")
    return updates
