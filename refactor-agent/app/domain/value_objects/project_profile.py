from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class ProjectProfile:
    """Immutable description of the project's technology stack and conventions.

    Detected once per run and used to select the applicable engineering policies.
    """

    name: str
    language: str
    framework: Optional[str]
    test_framework: Optional[str]
    has_type_hints: bool
    detected_patterns: tuple[str, ...] = field(default_factory=tuple)
