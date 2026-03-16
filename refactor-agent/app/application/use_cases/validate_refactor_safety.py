from typing import List, Optional

from app.application.policies.refactor_safety_policy import RefactorSafetyPolicy
from app.application.ports.outbound.validation_runner_port import ValidationRunnerPort
from app.domain.entities.changed_file import ChangedFile
from app.domain.entities.refactor_suggestion import RefactorSuggestion
from app.domain.value_objects.project_profile import ProjectProfile
from app.domain.value_objects.validation_result import ValidationResult


class ValidateRefactorSafetyUseCase:
    """Use case: verify that proposed refactor suggestions satisfy all safety gates.

    Two-stage validation:
    1. Policy-level checks (fast, in-process) against RefactorSuggestion objects.
    2. Repo-aware validation planning (via ValidationRunnerPort) against the scoped repo state.

    Stage 2 is optional and should remain non-intrusive unless a later apply-capable
    phase explicitly enables command execution.
    """

    def __init__(
        self,
        safety_policy: RefactorSafetyPolicy,
        validation_runner: Optional[ValidationRunnerPort] = None,
    ) -> None:
        self._safety_policy = safety_policy
        self._validation_runner = validation_runner

    def execute(
        self,
        suggestions: List[RefactorSuggestion],
        changed_files: List[ChangedFile],
        repo_path: str,
        profile: ProjectProfile,
    ) -> ValidationResult:
        # Stage 1: policy-level checks
        policy_result = self._safety_policy.evaluate(suggestions, changed_files, profile)
        if not policy_result.passed:
            return policy_result

        if self._validation_runner is not None:
            return self._validation_runner.validate(repo_path, profile, changed_files)

        return policy_result
