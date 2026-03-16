from pathlib import Path
import subprocess

from app.domain.entities.refactor_patch import RefactorPatch
from app.domain.enums.refactor_status import RefactorStatus
from app.infrastructure.adapters.git.review_branch_publisher_adapter import (
    GitReviewBranchPublisherAdapter,
)
from app.infrastructure.adapters.refactor.filesystem_refactor_executor_adapter import (
    FileSystemRefactorExecutorAdapter,
)


def _run_git(repo_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )


class TestGitReviewBranchPublisherAdapterIntegration:
    def test_materializes_review_branch_without_touching_main_checkout(self, tmp_path: Path) -> None:
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        _run_git(repo_path, "init", "-b", "main")
        _run_git(repo_path, "config", "user.name", "Test User")
        _run_git(repo_path, "config", "user.email", "test@example.com")

        target_file = repo_path / "app.py"
        target_file.write_text("def run():\n    return 1\n", encoding="utf-8")
        _run_git(repo_path, "add", "app.py")
        _run_git(repo_path, "commit", "-m", "initial")

        publisher = GitReviewBranchPublisherAdapter(FileSystemRefactorExecutorAdapter())
        result = publisher.publish(
            [
                RefactorPatch(
                    suggestion_id="suggestion-1",
                    file_path=Path("app.py"),
                    original_chunk="return 1",
                    patched_chunk="return build_value()",
                    status=RefactorStatus.VALIDATED,
                )
            ],
            str(repo_path),
            "main",
            branch_name="ticket123_refactor",
        )

        assert result.branch_name == "ticket123_refactor"
        assert result.commit_sha
        assert target_file.read_text(encoding="utf-8") == "def run():\n    return 1\n"

        branch_file = _run_git(repo_path, "show", "ticket123_refactor:app.py").stdout
        assert "return build_value()" in branch_file

    def test_rolls_back_branch_when_patch_application_fails(self, tmp_path: Path) -> None:
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        _run_git(repo_path, "init", "-b", "main")
        _run_git(repo_path, "config", "user.name", "Test User")
        _run_git(repo_path, "config", "user.email", "test@example.com")

        target_file = repo_path / "app.py"
        target_file.write_text("def run():\n    return 1\n", encoding="utf-8")
        _run_git(repo_path, "add", "app.py")
        _run_git(repo_path, "commit", "-m", "initial")

        publisher = GitReviewBranchPublisherAdapter(FileSystemRefactorExecutorAdapter())

        try:
            publisher.publish(
                [
                    RefactorPatch(
                        suggestion_id="suggestion-1",
                        file_path=Path("app.py"),
                        original_chunk="return missing()",
                        patched_chunk="return build_value()",
                        status=RefactorStatus.VALIDATED,
                    )
                ],
                str(repo_path),
                "main",
                branch_name="ticket123_refactor",
            )
        except RuntimeError as exc:
            assert "No approved refactor patches could be applied" in str(exc)
        else:
            raise AssertionError("Expected branch materialization failure")

        branches = _run_git(repo_path, "branch", "--list", "ticket123_refactor").stdout.strip()
        assert branches == ""