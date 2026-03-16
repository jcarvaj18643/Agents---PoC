from abc import ABC, abstractmethod

from app.domain.entities.changed_file import ChangedFile
from app.domain.value_objects.project_profile import ProjectProfile
from app.domain.value_objects.validation_result import ValidationResult


class ValidationRunnerPort(ABC):
    """Outbound port — runs stack-specific validation commands for the target repo."""

    @abstractmethod
    def validate(
        self,
        repo_path: str,
        profile: ProjectProfile,
        changed_files: list[ChangedFile],
    ) -> ValidationResult:
        ...
