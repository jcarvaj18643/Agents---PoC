from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Signal:
    name: str
    direction: str
    weight: float
    source: str
    rationale: str
