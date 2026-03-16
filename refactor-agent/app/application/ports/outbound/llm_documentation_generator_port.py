from abc import ABC, abstractmethod
from typing import List

from app.domain.entities.changed_file import ChangedFile
from app.domain.entities.documentation_artifact import DocumentationArtifact
from app.domain.value_objects.engineering_policy import EngineeringPolicy


class LlmDocumentationGeneratorPort(ABC):
    """Outbound port — generates documentation artifacts via an LLM for changed files."""

    @abstractmethod
    def generate(
        self,
        files: List[ChangedFile],
        policies: List[EngineeringPolicy],
    ) -> List[DocumentationArtifact]:
        ...
