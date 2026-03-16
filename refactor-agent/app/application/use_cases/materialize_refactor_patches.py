from typing import List

from app.application.ports.outbound.refactor_executor_port import RefactorExecutorPort
from app.domain.entities.refactor_patch import RefactorPatch
from app.domain.entities.refactor_suggestion import RefactorSuggestion
from app.domain.value_objects.validation_result import ValidationResult


class MaterializeRefactorPatchesUseCase:
    """Prepare patch previews and optionally apply them under strict safety gates."""

    def __init__(self, refactor_executor: RefactorExecutorPort) -> None:
        self._refactor_executor = refactor_executor

    def execute(
        self,
        suggestions: List[RefactorSuggestion],
        repo_path: str,
        validation_result: ValidationResult,
        apply_changes: bool,
    ) -> List[RefactorPatch]:
        patches = self._refactor_executor.prepare(suggestions, repo_path)
        if not apply_changes or not validation_result.passed:
            return patches
        return self._refactor_executor.apply(patches, repo_path)