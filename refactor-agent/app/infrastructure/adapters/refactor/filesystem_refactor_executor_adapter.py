from pathlib import Path

from app.application.ports.outbound.refactor_executor_port import RefactorExecutorPort
from app.domain.entities.refactor_patch import RefactorPatch
from app.domain.entities.refactor_suggestion import RefactorSuggestion
from app.domain.enums.refactor_status import RefactorStatus


class FileSystemRefactorExecutorAdapter(RefactorExecutorPort):
    """Prepare and apply refactor patches against a local repository checkout."""

    def prepare(self, suggestions: list[RefactorSuggestion], repo_path: str) -> list[RefactorPatch]:
        repo_root = Path(repo_path).resolve()
        return [self._prepare_patch(suggestion, repo_root) for suggestion in suggestions]

    def apply(self, patches: list[RefactorPatch], repo_path: str) -> list[RefactorPatch]:
        repo_root = Path(repo_path).resolve()
        applied_patches: list[RefactorPatch] = []

        for patch in patches:
            if patch.status != RefactorStatus.VALIDATED:
                applied_patches.append(patch)
                continue

            absolute_path = self._resolve_repo_file(repo_root, patch.file_path)
            if absolute_path is None or not absolute_path.exists():
                applied_patches.append(self._replace_status(patch, RefactorStatus.FAILED))
                continue

            current_content = absolute_path.read_text(encoding="utf-8")
            if current_content.count(patch.original_chunk) != 1:
                applied_patches.append(self._replace_status(patch, RefactorStatus.FAILED))
                continue

            updated_content = current_content.replace(patch.original_chunk, patch.patched_chunk, 1)
            absolute_path.write_text(updated_content, encoding="utf-8")
            applied_patches.append(self._replace_status(patch, RefactorStatus.APPLIED, applied=True))

        return applied_patches

    def _prepare_patch(self, suggestion: RefactorSuggestion, repo_root: Path) -> RefactorPatch:
        file_path = Path(suggestion.file_path)
        original_chunk = suggestion.change_anchor or ""
        patched_chunk = suggestion.suggested_code or ""

        if not original_chunk or not patched_chunk:
            return RefactorPatch(
                suggestion_id=suggestion.id,
                file_path=file_path,
                original_chunk=original_chunk,
                patched_chunk=patched_chunk,
                status=RefactorStatus.REJECTED,
            )

        absolute_path = self._resolve_repo_file(repo_root, file_path)
        if absolute_path is None or not absolute_path.exists():
            return RefactorPatch(
                suggestion_id=suggestion.id,
                file_path=file_path,
                original_chunk=original_chunk,
                patched_chunk=patched_chunk,
                status=RefactorStatus.REJECTED,
            )

        file_content = absolute_path.read_text(encoding="utf-8")
        status = RefactorStatus.VALIDATED if file_content.count(original_chunk) == 1 else RefactorStatus.REJECTED
        return RefactorPatch(
            suggestion_id=suggestion.id,
            file_path=file_path,
            original_chunk=original_chunk,
            patched_chunk=patched_chunk,
            status=status,
        )

    def _resolve_repo_file(self, repo_root: Path, file_path: Path) -> Path | None:
        candidate = (repo_root / file_path).resolve()
        try:
            candidate.relative_to(repo_root)
        except ValueError:
            return None
        return candidate

    def _replace_status(
        self,
        patch: RefactorPatch,
        status: RefactorStatus,
        applied: bool = False,
    ) -> RefactorPatch:
        return RefactorPatch(
            suggestion_id=patch.suggestion_id,
            file_path=patch.file_path,
            original_chunk=patch.original_chunk,
            patched_chunk=patch.patched_chunk,
            status=status,
            applied=applied,
        )