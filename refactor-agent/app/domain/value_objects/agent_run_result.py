from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from app.domain.entities.changed_file import ChangedFile
from app.domain.entities.documentation_artifact import DocumentationArtifact
from app.domain.entities.refactor_patch import RefactorPatch
from app.domain.entities.refactor_suggestion import RefactorSuggestion
from app.domain.value_objects.engineering_policy import EngineeringPolicy
from app.domain.value_objects.project_profile import ProjectProfile
from app.domain.value_objects.pull_request_comment_publication import (
    PullRequestCommentPublication,
)
from app.domain.value_objects.pull_request_publication import PullRequestPublication
from app.domain.value_objects.review_branch_materialization import (
    ReviewBranchMaterialization,
)
from app.domain.value_objects.validation_result import ValidationResult


@dataclass
class AgentRunResult:
    """Final outcome of a complete agent governance run.

    Aggregates all artifacts produced across the pipeline steps
    so they can be published as a unified report.
    """

    run_id: str
    success: bool
    completed_at: datetime
    changed_files: List[ChangedFile] = field(default_factory=list)
    project_profile: Optional[ProjectProfile] = None
    applied_policies: List[EngineeringPolicy] = field(default_factory=list)
    documentation_artifacts: List[DocumentationArtifact] = field(default_factory=list)
    refactor_suggestions: List[RefactorSuggestion] = field(default_factory=list)
    refactor_patches: List[RefactorPatch] = field(default_factory=list)
    review_branch: Optional[ReviewBranchMaterialization] = None
    review_pull_request: Optional[PullRequestPublication] = None
    pull_request_comment: Optional[PullRequestCommentPublication] = None
    llm_stage_modes: dict[str, str] = field(default_factory=dict)
    validation_result: Optional[ValidationResult] = None
    report_path: Optional[str] = None
    error_message: Optional[str] = None

    @property
    def execution_status(self) -> str:
        return "completed" if self.success else "failed"

    @property
    def governance_status(self) -> str:
        if not self.success:
            return "failed"
        if self.validation_result is None:
            return "not-evaluated"
        if self.validation_result.status.value == "safe":
            return "eligible"
        if self.validation_result.status.value == "skipped":
            return "deferred-to-ci"
        return "blocked"
