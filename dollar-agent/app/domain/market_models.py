from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MarketSnapshot:
    usd_cop: float | None = None
    dxy: float | None = None
    brent_oil: float | None = None
    sp500: float | None = None
    vix: float | None = None


@dataclass
class MacroSnapshot:
    fed_narrative: str = "unknown"
    banrep_narrative: str = "unknown"
    colombia_inflation_narrative: str = "unknown"
    risk_sentiment: str = "mixed"
