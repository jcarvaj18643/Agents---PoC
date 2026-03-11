from __future__ import annotations

import logging

from app.services.scenario_service import ScenarioService
from app.state import AgentState


logger = logging.getLogger(__name__)


def run(state: AgentState, service: ScenarioService) -> AgentState:
    logger.info("node=build_scenarios start")

    scenario_analysis, warnings = service.build(
        user_query=state.get("user_query", ""),
        ranked_signals=state.get("ranked_signals", []),
        filtered_news=state.get("filtered_news", []),
        degraded_mode=state.get("degraded_mode", False),
        output_language=state.get("output_language", "spanish"),
    )

    logger.info("node=build_scenarios done")

    return {
        "scenario_analysis": scenario_analysis,
        "warnings": list(state.get("warnings", [])) + warnings,
        "error": None,
    }
