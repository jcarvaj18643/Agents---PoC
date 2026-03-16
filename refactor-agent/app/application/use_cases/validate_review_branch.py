from app.application.ports.outbound.review_branch_validator_port import (
    ReviewBranchValidatorPort,
)
from app.domain.entities.changed_file import ChangedFile
from app.domain.value_objects.project_profile import ProjectProfile
from app.domain.value_objects.review_branch_materialization import (
    ReviewBranchMaterialization,
)
from app.domain.value_objects.validation_result import ValidationResult


class ValidateReviewBranchUseCase:
    """Execute validation against the generated review branch before PR promotion."""

    def __init__(self, review_branch_validator: ReviewBranchValidatorPort) -> None:
        self._review_branch_validator = review_branch_validator

    def execute(
        self,
        review_branch: ReviewBranchMaterialization | None,
        repo_path: str,
        profile: ProjectProfile,
        changed_files: list[ChangedFile],
        enabled: bool,
    ) -> ValidationResult | None:
        if not enabled or review_branch is None:
            return None

        return self._review_branch_validator.validate(
            review_branch=review_branch,
            repo_path=repo_path,
            profile=profile,
            changed_files=changed_files,
        )