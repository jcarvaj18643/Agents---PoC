from abc import ABC, abstractmethod
from typing import List

from app.domain.entities.refactor_patch import RefactorPatch
from app.domain.entities.refactor_suggestion import RefactorSuggestion


class RefactorExecutorPort(ABC):
    """Outbound port — applies validated refactor suggestions to the filesystem as patches."""

    @abstractmethod
    def prepare(self, suggestions: List[RefactorSuggestion], repo_path: str) -> List[RefactorPatch]:
        ...

    @abstractmethod
    def apply(self, patches: List[RefactorPatch], repo_path: str) -> List[RefactorPatch]:
        ...
