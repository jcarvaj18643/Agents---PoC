from abc import ABC, abstractmethod
from typing import List

from app.domain.entities.refactor_patch import RefactorPatch
from app.domain.value_objects.review_branch_materialization import (
    ReviewBranchMaterialization,
)


class ReviewBranchPublisherPort(ABC):
    """Outbound port for materializing approved patches into a review branch."""

    @abstractmethod
    def publish(
        self,
        patches: List[RefactorPatch],
        repo_path: str,
        start_ref: str,
        branch_name: str | None = None,
        push: bool = False,
        remote_name: str = "origin",
    ) -> ReviewBranchMaterialization:
        ...