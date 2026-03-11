from __future__ import annotations


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def weighted_score(weights: list[float]) -> float:
    if not weights:
        return 0.0
    return sum(weights) / len(weights)
