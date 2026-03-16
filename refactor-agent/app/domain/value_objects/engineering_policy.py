from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class EngineeringPolicy:
    """An immutable set of rules that govern documentation and refactoring behaviour.

    Policies are loaded from an external source (YAML, DB, etc.) and matched
    to the detected project profile before being passed to LLM prompts.
    """

    id: str
    name: str
    description: str
    applies_to: tuple[str, ...]  # language patterns or file globs (e.g. ["*.py"])
    rules: tuple[Dict[str, Any], ...]
    version: str = "1.0.0"
