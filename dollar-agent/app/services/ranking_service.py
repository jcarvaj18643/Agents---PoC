from __future__ import annotations


class RankingService:
    def rank(self, signals: list[dict[str, str | float]]) -> list[dict[str, str | float]]:
        def score(signal: dict[str, str | float]) -> float:
            value = signal.get("weight", 0.0)
            return float(value) if isinstance(value, (float, int)) else 0.0

        return sorted(signals, key=score, reverse=True)
