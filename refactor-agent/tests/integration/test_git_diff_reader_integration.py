"""Integration tests for GitDiffReaderAdapter using a temporary git repository."""

from pathlib import Path
import subprocess

from app.domain.enums.change_type import ChangeType
from app.infrastructure.adapters.git.git_diff_reader_adapter import GitDiffReaderAdapter
from app.infrastructure.parsers.diff_parser import DiffParser


def _run_git(repo_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )


class TestGitDiffReaderAdapterIntegration:
    def test_reads_real_git_diff_from_temp_repo(self, tmp_path: Path) -> None:
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        _run_git(repo_path, "init", "-b", "main")
        _run_git(repo_path, "config", "user.name", "Test User")
        _run_git(repo_path, "config", "user.email", "test@example.com")

        target_file = repo_path / "app.py"
        target_file.write_text("def run():\n    return 1\n", encoding="utf-8")
        _run_git(repo_path, "add", "app.py")
        _run_git(repo_path, "commit", "-m", "initial")

        _run_git(repo_path, "checkout", "-b", "feature/diff-test")

        target_file.write_text("def run():\n    return 2\n", encoding="utf-8")
        _run_git(repo_path, "add", "app.py")
        _run_git(repo_path, "commit", "-m", "update")

        adapter = GitDiffReaderAdapter(diff_parser=DiffParser())
        scope = adapter.read_diff("main", "HEAD", str(repo_path))

        assert scope.total_files == 1
        assert scope.changed_files[0].path.as_posix() == "app.py"
        assert scope.changed_files[0].change_type == ChangeType.MODIFIED

    def test_reads_real_git_diff_from_nested_frontend_path(self, tmp_path: Path) -> None:
        repo_path = tmp_path / "repo"
        frontend_path = repo_path / "angular_frontend"
        source_file = frontend_path / "src" / "app" / "app.component.ts"

        source_file.parent.mkdir(parents=True)

        _run_git(repo_path, "init", "-b", "main")
        _run_git(repo_path, "config", "user.name", "Test User")
        _run_git(repo_path, "config", "user.email", "test@example.com")

        (frontend_path / "package.json").write_text('{"dependencies": {"@angular/core": "19.0.0"}}', encoding="utf-8")
        (frontend_path / "angular.json").write_text('{"projects": {"web": {}}}', encoding="utf-8")
        source_file.write_text("export class AppComponent {}\n", encoding="utf-8")
        _run_git(repo_path, "add", ".")
        _run_git(repo_path, "commit", "-m", "initial")

        _run_git(repo_path, "checkout", "-b", "feature/frontend-diff")

        source_file.write_text("export class AppComponent {\n  title = 'demo';\n}\n", encoding="utf-8")
        _run_git(repo_path, "add", str(source_file.relative_to(repo_path)))
        _run_git(repo_path, "commit", "-m", "update frontend")

        adapter = GitDiffReaderAdapter(diff_parser=DiffParser())
        scope = adapter.read_diff("main", "HEAD", str(frontend_path))

        assert scope.total_files == 1
        assert scope.changed_files[0].path.as_posix() == "src/app/app.component.ts"
        assert scope.changed_files[0].change_type == ChangeType.MODIFIED

    def test_reads_worktree_diff_from_nested_frontend_path(self, tmp_path: Path) -> None:
        repo_path = tmp_path / "repo"
        frontend_path = repo_path / "angular_frontend"
        source_file = frontend_path / "src" / "app" / "app.component.ts"

        source_file.parent.mkdir(parents=True)

        _run_git(repo_path, "init", "-b", "main")
        _run_git(repo_path, "config", "user.name", "Test User")
        _run_git(repo_path, "config", "user.email", "test@example.com")

        (frontend_path / "package.json").write_text('{"dependencies": {"@angular/core": "19.0.0"}}', encoding="utf-8")
        (frontend_path / "angular.json").write_text('{"projects": {"web": {}}}', encoding="utf-8")
        source_file.write_text("export class AppComponent {}\n", encoding="utf-8")
        _run_git(repo_path, "add", ".")
        _run_git(repo_path, "commit", "-m", "initial")

        source_file.write_text("export class AppComponent {\n  title = 'local';\n}\n", encoding="utf-8")

        adapter = GitDiffReaderAdapter(diff_parser=DiffParser())
        scope = adapter.read_diff("HEAD", "WORKTREE", str(frontend_path))

        assert scope.total_files == 1
        assert scope.changed_files[0].path.as_posix() == "src/app/app.component.ts"
        assert scope.changed_files[0].change_type == ChangeType.MODIFIED