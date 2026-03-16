from abc import ABC, abstractmethod

from app.domain.entities.changed_file import ChangedFile
from app.domain.value_objects.project_profile import ProjectProfile
from app.domain.value_objects.review_branch_materialization import (
    ReviewBranchMaterialization,
)
from app.domain.value_objects.validation_result import ValidationResult


class ReviewBranchValidatorPort(ABC):
    """Outbound port — validates a materialized review branch in an isolated checkout."""

    @abstractmethod
    def validate(
        self,
        review_branch: ReviewBranchMaterialization,
        repo_path: str,
        profile: ProjectProfile,
        changed_files: list[ChangedFile],
    ) -> ValidationResult:
        ...