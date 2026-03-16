from dataclasses import dataclass

from app.domain.entities.changed_symbol import ChangedSymbol


@dataclass(frozen=True)
class SymbolContext:
    """Resolved structural context for the symbol impacted by a changed hunk."""

    symbol: ChangedSymbol | None = None
    snippet: str = ""