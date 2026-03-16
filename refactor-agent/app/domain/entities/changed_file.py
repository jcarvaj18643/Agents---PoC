from dataclasses import dataclass
from pathlib import Path

from app.domain.entities.changed_symbol import ChangedSymbol
from app.domain.enums.change_type import ChangeType
from app.domain.enums.language import Language


@dataclass(frozen=True)
class ChangedFile:
    """Represents a single file that was affected by the git diff.

    This is an immutable entity: it captures the state of a changed file
    at the moment the diff was parsed and must not be mutated.
    """

    path: Path
    change_type: ChangeType
    language: Language
    diff_content: str
    added_lines: int = 0
    removed_lines: int = 0
    changed_line_numbers: tuple[int, ...] = ()
    context_snapshot: str = ""
    full_file_context: str = ""
    symbol_context: str = ""
    impacted_symbol: ChangedSymbol | None = None

    @property
    def changed_hunk_context(self) -> str:
        return self.context_snapshot
