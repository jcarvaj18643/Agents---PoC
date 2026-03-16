from dataclasses import dataclass

from app.domain.enums.change_type import ChangeType


@dataclass(frozen=True)
class ChangedSymbol:
    """A named code element (function, class, method) touched by the diff.

    Symbols allow the agent to reason at a finer granularity than whole files.
    """

    name: str
    symbol_type: str  # "function", "class", "method", "constant", …
    change_type: ChangeType
    file_path: str
    start_line: int
    end_line: int
