from dataclasses import dataclass
from pathlib import Path

from app.domain.enums.refactor_status import RefactorStatus


@dataclass
class RefactorPatch:
    """A concrete, diff-like patch produced from a validated RefactorSuggestion.

    Patches are the directly applicable units of change that the
    RefactorExecutorPort writes to the filesystem.
    """

    suggestion_id: str
    file_path: Path
    original_chunk: str
    patched_chunk: str
    status: RefactorStatus
    applied: bool = False
