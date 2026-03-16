from pathlib import Path

from app.domain.entities.refactor_suggestion import RefactorSuggestion
from app.domain.enums.refactor_status import RefactorStatus
from app.domain.enums.severity import Severity
from app.infrastructure.adapters.refactor.filesystem_refactor_executor_adapter import (
    FileSystemRefactorExecutorAdapter,
)


class TestFileSystemRefactorExecutorAdapter:
    def test_prepares_validated_patch_when_anchor_and_code_match_file(self, tmp_path: Path) -> None:
        repo_file = tmp_path / "app.py"
        repo_file.write_text("def run():\n    return 1\n", encoding="utf-8")
        adapter = FileSystemRefactorExecutorAdapter()

        patches = adapter.prepare(
            [
                RefactorSuggestion(
                    id="suggestion-1",
                    title="Extract helper",
                    description="Use a helper.",
                    file_path="app.py",
                    severity=Severity.INFO,
                    rationale="Local replacement is clear.",
                    change_anchor="return 1",
                    suggested_code="return build_value()",
                )
            ],
            str(tmp_path),
        )

        assert len(patches) == 1
        assert patches[0].status == RefactorStatus.VALIDATED

    def test_applies_validated_patch_to_file(self, tmp_path: Path) -> None:
        repo_file = tmp_path / "app.py"
        repo_file.write_text("def run():\n    return 1\n", encoding="utf-8")
        adapter = FileSystemRefactorExecutorAdapter()
        patches = adapter.prepare(
            [
                RefactorSuggestion(
                    id="suggestion-1",
                    title="Extract helper",
                    description="Use a helper.",
                    file_path="app.py",
                    severity=Severity.INFO,
                    rationale="Local replacement is clear.",
                    change_anchor="return 1",
                    suggested_code="return build_value()",
                )
            ],
            str(tmp_path),
        )

        applied = adapter.apply(patches, str(tmp_path))

        assert applied[0].status == RefactorStatus.APPLIED
        assert applied[0].applied is True
        assert "return build_value()" in repo_file.read_text(encoding="utf-8")

    def test_rejects_patch_without_executable_code(self, tmp_path: Path) -> None:
        repo_file = tmp_path / "app.py"
        repo_file.write_text("def run():\n    return 1\n", encoding="utf-8")
        adapter = FileSystemRefactorExecutorAdapter()

        patches = adapter.prepare(
            [
                RefactorSuggestion(
                    id="suggestion-1",
                    title="Extract helper",
                    description="Use a helper.",
                    file_path="app.py",
                    severity=Severity.INFO,
                    rationale="Needs code.",
                    change_anchor="return 1",
                )
            ],
            str(tmp_path),
        )

        assert patches[0].status == RefactorStatus.REJECTED