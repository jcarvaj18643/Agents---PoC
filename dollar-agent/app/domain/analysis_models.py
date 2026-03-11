from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Scenario:
    name: str
    direction: str
    probability_label: str
    narrative: str


@dataclass
class ValidationResult:
    is_valid: bool
    issues: list[str]
    confidence_level: str
