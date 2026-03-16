from dataclasses import dataclass, field
from typing import List

from app.domain.entities.changed_file import ChangedFile
from app.domain.entities.changed_symbol import ChangedSymbol


@dataclass
class CodeScope:
    """The full scope of code affected by a git diff.

    Acts as the primary aggregate for a single agent run: every downstream
    use case receives or derives from a CodeScope instance.
    """

    changed_files: List[ChangedFile] = field(default_factory=list)
    changed_symbols: List[ChangedSymbol] = field(default_factory=list)
    base_ref: str = ""
    head_ref: str = ""

    @property
    def total_files(self) -> int:
        return len(self.changed_files)

    @property
    def is_empty(self) -> bool:
        return len(self.changed_files) == 0
