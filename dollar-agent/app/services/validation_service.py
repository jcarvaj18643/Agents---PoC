from __future__ import annotations

from app.domain.analysis_models import ValidationResult


class ValidationService:
    def validate(
        self,
        market_data: dict[str, object],
        filtered_news: list[dict[str, str]],
        ranked_signals: list[dict[str, object]],
        degraded_mode: bool,
    ) -> ValidationResult:
        issues: list[str] = []

        available_market = sum(1 for value in market_data.values() if value is not None)
        if available_market < 2:
            issues.append("Insufficient market indicators available.")

        news_count = len(filtered_news)
        signals_count = len(ranked_signals)
        strong_macro_coverage = available_market >= 3 and signals_count >= 5

        if news_count < 2 and not strong_macro_coverage:
            issues.append("Too few relevant news items.")

        if signals_count < 4:
            issues.append("Too few usable directional signals.")

        confidence = "high"
        if issues and len(issues) <= 2:
            confidence = "medium"
        if issues and (len(issues) > 2 or degraded_mode):
            confidence = "low"

        # If only news coverage is weak but macro/market signals are strong, keep medium confidence.
        if not degraded_mode and not issues and news_count < 3 and strong_macro_coverage:
            confidence = "medium"

        return ValidationResult(
            is_valid=not issues,
            issues=issues,
            confidence_level=confidence,
        )
