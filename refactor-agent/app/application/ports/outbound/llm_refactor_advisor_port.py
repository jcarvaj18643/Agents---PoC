from abc import ABC, abstractmethod
from typing import List

from app.domain.entities.changed_file import ChangedFile
from app.domain.entities.refactor_suggestion import RefactorSuggestion
from app.domain.value_objects.engineering_policy import EngineeringPolicy


class LlmRefactorAdvisorPort(ABC):
    """Outbound port — generates refactoring suggestions via an LLM based on policies."""

    @abstractmethod
    def advise(
        self,
        files: List[ChangedFile],
        policies: List[EngineeringPolicy],
    ) -> List[RefactorSuggestion]:
        ...
