from __future__ import annotations

import logging

from app.services.market_data_service import MarketDataService
from app.state import AgentState


logger = logging.getLogger(__name__)


def run(state: AgentState, service: MarketDataService) -> AgentState:
    logger.info("node=fetch_market_data start")
    market_data, warnings = service.fetch_snapshot()

    logger.info(
        "node=fetch_market_data done indicators=%s",
        sum(1 for v in market_data.values() if v is not None),
    )

    return {
        "market_data": market_data,
        "warnings": list(state.get("warnings", [])) + warnings,
        "error": None,
    }
