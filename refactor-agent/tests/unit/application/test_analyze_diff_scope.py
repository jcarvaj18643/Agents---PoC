"""Unit tests for AnalyzeDiffScopeUseCase.

Uses a fake (in-memory) GitDiffReaderPort to keep the test hermetic.
"""

from pathlib import Path

from app.application.ports.outbound.git_diff_reader_port import GitDiffReaderPort
from app.application.use_cases.analyze_diff_scope import AnalyzeDiffScopeUseCase
from app.domain.entities.changed_file import ChangedFile
from app.domain.entities.code_scope import CodeScope
from app.domain.enums.change_type import ChangeType
from app.domain.enums.language import Language


class _FakeGitDiffReader(GitDiffReaderPort):
    """Test double: returns a pre-configured CodeScope."""

    def __init__(self, scope: CodeScope) -> None:
        self._scope = scope
        self.calls: list[tuple[str, str, str]] = []

    def read_diff(self, base_ref: str, head_ref: str, repo_path: str) -> CodeScope:
        self.calls.append((base_ref, head_ref, repo_path))
        return self._scope


class TestAnalyzeDiffScopeUseCase:
    def test_returns_scope_produced_by_reader(self) -> None:
        expected = CodeScope(
            changed_files=[
                ChangedFile(
                    path=Path("app/service.py"),
                    change_type=ChangeType.MODIFIED,
                    language=Language.PYTHON,
                    diff_content="",
                )
            ],
            base_ref="main",
            head_ref="feature",
        )
        use_case = AnalyzeDiffScopeUseCase(diff_reader=_FakeGitDiffReader(expected))
        result = use_case.execute("main", "feature", "/repo")

        assert result.total_files == 1
        assert result.changed_files[0].path == Path("app/service.py")

    def test_passes_correct_args_to_reader(self) -> None:
        fake_reader = _FakeGitDiffReader(CodeScope())
        AnalyzeDiffScopeUseCase(diff_reader=fake_reader).execute(
            "origin/main", "HEAD", "/workspace"
        )
        assert fake_reader.calls == [("origin/main", "HEAD", "/workspace")]

    def test_empty_scope_is_handled(self) -> None:
        use_case = AnalyzeDiffScopeUseCase(
            diff_reader=_FakeGitDiffReader(CodeScope(base_ref="main", head_ref="feature"))
        )
        result = use_case.execute("main", "feature", "/repo")
        assert result.is_empty is True

    def test_excludes_generated_and_vendor_files(self) -> None:
        scope = CodeScope(
            changed_files=[
                ChangedFile(
                    path=Path("dist/bundle.min.js"),
                    change_type=ChangeType.ADDED,
                    language=Language.JAVASCRIPT,
                    diff_content="",
                ),
                ChangedFile(
                    path=Path("app/service.py"),
                    change_type=ChangeType.MODIFIED,
                    language=Language.PYTHON,
                    diff_content="",
                ),
            ]
        )
        use_case = AnalyzeDiffScopeUseCase(diff_reader=_FakeGitDiffReader(scope))

        result = use_case.execute("main", "feature", "/repo")

        assert result.total_files == 1
        assert result.changed_files[0].path == Path("app/service.py")
