from __future__ import annotations

from app.config import settings


class MacroDataClient:
    def get_macro_context(self) -> dict[str, str]:
        # PoC assumption-based context placeholders.
        # This adapter can be replaced later with premium macro feeds.
        return {
            "fed_narrative": "higher_for_longer_risk",
            "banrep_narrative": "gradual_easing_bias",
            "colombia_inflation_narrative": "disinflation_but_sticky",
            "analysis_horizon_default": settings.default_analysis_horizon,
        }
