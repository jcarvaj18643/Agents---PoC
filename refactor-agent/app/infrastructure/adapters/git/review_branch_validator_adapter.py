import shutil
import subprocess
import tempfile
from pathlib import Path

from app.application.ports.outbound.review_branch_validator_port import (
    ReviewBranchValidatorPort,
)
from app.application.ports.outbound.validation_runner_port import ValidationRunnerPort
from app.domain.entities.changed_file import ChangedFile
from app.domain.value_objects.project_profile import ProjectProfile
from app.domain.value_objects.review_branch_materialization import (
    ReviewBranchMaterialization,
)
from app.domain.value_objects.validation_result import ValidationResult


class GitReviewBranchValidatorAdapter(ReviewBranchValidatorPort):
    """Validate a materialized review branch inside an isolated git worktree."""

    def __init__(self, validation_runner: ValidationRunnerPort) -> None:
        self._validation_runner = validation_runner

    def validate(
        self,
        review_branch: ReviewBranchMaterialization,
        repo_path: str,
        profile: ProjectProfile,
        changed_files: list[ChangedFile],
    ) -> ValidationResult:
        repo_root = Path(repo_path).resolve()
        worktree_path = Path(tempfile.mkdtemp(prefix="refactor-validate-"))

        try:
            self._run_git(
                repo_root,
                "worktree",
                "add",
                "--detach",
                str(worktree_path),
                review_branch.branch_name,
            )
            return self._validation_runner.validate(
                str(worktree_path),
                profile,
                changed_files,
            )
        finally:
            self._safe_remove_worktree(repo_root, worktree_path)

    def _run_git(self, cwd: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip() or "unknown git failure"
            raise RuntimeError(f"git {' '.join(args)} failed: {stderr}")
        return result.stdout.strip()

    def _safe_remove_worktree(self, repo_root: Path, worktree_path: Path) -> None:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree_path)],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        shutil.rmtree(worktree_path, ignore_errors=True)