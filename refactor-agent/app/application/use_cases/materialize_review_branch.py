from typing import List

from app.application.ports.outbound.review_branch_publisher_port import (
    ReviewBranchPublisherPort,
)
from app.domain.entities.refactor_patch import RefactorPatch
from app.domain.enums.refactor_status import RefactorStatus
from app.domain.value_objects.review_branch_materialization import (
    ReviewBranchMaterialization,
)
from app.domain.value_objects.validation_result import ValidationResult


class MaterializeReviewBranchUseCase:
    """Create a dedicated review branch from approved refactor patches."""

    def __init__(self, review_branch_publisher: ReviewBranchPublisherPort) -> None:
        self._review_branch_publisher = review_branch_publisher

    def execute(
        self,
        patches: List[RefactorPatch],
        repo_path: str,
        start_ref: str,
        validation_result: ValidationResult,
        enabled: bool,
        branch_name: str | None = None,
        push: bool = False,
        remote_name: str = "origin",
    ) -> ReviewBranchMaterialization | None:
        if not enabled or not validation_result.passed:
            return None

        approved_patches = [
            patch
            for patch in patches
            if patch.status in {RefactorStatus.VALIDATED, RefactorStatus.APPLIED}
        ]
        if not approved_patches:
            return None

        return self._review_branch_publisher.publish(
            approved_patches,
            repo_path,
            start_ref,
            branch_name=branch_name,
            push=push,
            remote_name=remote_name,
        )