"""Unit tests for GitDiffReaderAdapter."""

from pathlib import Path

import pytest

from app.domain.entities.code_scope import CodeScope
from app.domain.enums.change_type import ChangeType
from app.infrastructure.adapters.git.git_diff_reader_adapter import GitDiffReaderAdapter
from app.infrastructure.parsers.diff_parser import DiffParser
from tests.fixtures.sample_diff import EMPTY_DIFF, SAMPLE_UNIFIED_DIFF


class TestGitDiffReaderAdapter:
    def test_builds_git_diff_command_for_worktree(self) -> None:
        adapter = GitDiffReaderAdapter(diff_parser=DiffParser())

        command = adapter._build_git_diff_command("HEAD", "WORKTREE")

        assert command == [
            "git",
            "diff",
            "HEAD",
            "--no-ext-diff",
            "--find-renames",
            "--unified=3",
        ]

    def test_returns_empty_scope_when_git_diff_is_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        adapter = GitDiffReaderAdapter(diff_parser=DiffParser())

        monkeypatch.setattr(adapter, "_run_git_diff", lambda **_: EMPTY_DIFF)
        monkeypatch.setattr(adapter, "_get_relative_repo_subpath", lambda _: None)
        scope = adapter.read_diff("main", "feature", "/repo")

        assert isinstance(scope, CodeScope)
        assert scope.is_empty is True

    def test_scope_carries_correct_refs(self, monkeypatch: pytest.MonkeyPatch) -> None:
        adapter = GitDiffReaderAdapter(diff_parser=DiffParser())

        monkeypatch.setattr(adapter, "_run_git_diff", lambda **_: EMPTY_DIFF)
        monkeypatch.setattr(adapter, "_get_relative_repo_subpath", lambda _: None)
        scope = adapter.read_diff("origin/main", "HEAD", "/workspace")

        assert scope.base_ref == "origin/main"
        assert scope.head_ref == "HEAD"

    def test_parses_changed_file_from_git_diff(self, monkeypatch: pytest.MonkeyPatch) -> None:
        adapter = GitDiffReaderAdapter(diff_parser=DiffParser())

        monkeypatch.setattr(adapter, "_run_git_diff", lambda **_: SAMPLE_UNIFIED_DIFF)
        monkeypatch.setattr(adapter, "_get_relative_repo_subpath", lambda _: None)
        scope = adapter.read_diff("main", "feature", "/repo")

        assert scope.total_files == 1
        assert scope.changed_files[0].path.as_posix() == "app/service.py"
        assert scope.changed_files[0].change_type == ChangeType.MODIFIED

    def test_normalizes_paths_for_nested_repo_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        adapter = GitDiffReaderAdapter(diff_parser=DiffParser())
        nested_diff = """\
diff --git a/angular_frontend/src/app/app.component.ts b/angular_frontend/src/app/app.component.ts
index 1111111..2222222 100644
--- a/angular_frontend/src/app/app.component.ts
+++ b/angular_frontend/src/app/app.component.ts
@@ -1,1 +1,2 @@
 export class AppComponent {}
+// updated
"""

        monkeypatch.setattr(adapter, "_run_git_diff", lambda **_: nested_diff)
        monkeypatch.setattr(adapter, "_get_relative_repo_subpath", lambda _: Path("angular_frontend"))

        scope = adapter.read_diff("main", "HEAD", "/repo/angular_frontend")

        assert scope.total_files == 1
        assert scope.changed_files[0].path.as_posix() == "src/app/app.component.ts"

    def test_filters_files_outside_nested_repo_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        adapter = GitDiffReaderAdapter(diff_parser=DiffParser())
        mixed_diff = """\
diff --git a/angular_frontend/src/app/app.component.ts b/angular_frontend/src/app/app.component.ts
index 1111111..2222222 100644
--- a/angular_frontend/src/app/app.component.ts
+++ b/angular_frontend/src/app/app.component.ts
@@ -1,1 +1,2 @@
 export class AppComponent {}
+// updated
diff --git a/scripts/helper.py b/scripts/helper.py
index 3333333..4444444 100644
--- a/scripts/helper.py
+++ b/scripts/helper.py
@@ -1,1 +1,2 @@
 def helper():
+    return True
"""

        monkeypatch.setattr(adapter, "_run_git_diff", lambda **_: mixed_diff)
        monkeypatch.setattr(adapter, "_get_relative_repo_subpath", lambda _: Path("angular_frontend"))

        scope = adapter.read_diff("main", "HEAD", "/repo/angular_frontend")

        assert scope.total_files == 1
        assert scope.changed_files[0].path.as_posix() == "src/app/app.component.ts"

    def test_raises_on_git_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        adapter = GitDiffReaderAdapter(diff_parser=DiffParser())

        def _raise(*args: object, **kwargs: object) -> str:
            raise RuntimeError("git diff failed: bad revision")

        monkeypatch.setattr(adapter, "_run_git_diff", _raise)

        with pytest.raises(RuntimeError, match="bad revision"):
            adapter.read_diff("bad-ref", "HEAD", "/repo")
