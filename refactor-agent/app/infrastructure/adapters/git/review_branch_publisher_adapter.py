import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.application.ports.outbound.refactor_executor_port import RefactorExecutorPort
from app.application.ports.outbound.review_branch_publisher_port import (
    ReviewBranchPublisherPort,
)
from app.domain.entities.refactor_patch import RefactorPatch
from app.domain.enums.refactor_status import RefactorStatus
from app.domain.value_objects.review_branch_materialization import (
    ReviewBranchMaterialization,
)


class GitReviewBranchPublisherAdapter(ReviewBranchPublisherPort):
    """Materialize approved refactor patches into an isolated git review branch."""

    def __init__(
        self,
        refactor_executor: RefactorExecutorPort,
        commit_message: str = "chore(refactor-agent): materialize approved refactor patches",
    ) -> None:
        self._refactor_executor = refactor_executor
        self._commit_message = commit_message

    def publish(
        self,
        patches: list[RefactorPatch],
        repo_path: str,
        start_ref: str,
        branch_name: str | None = None,
        push: bool = False,
        remote_name: str = "origin",
    ) -> ReviewBranchMaterialization:
        repo_root = Path(repo_path).resolve()
        review_branch_name = branch_name or self._default_branch_name(start_ref)
        worktree_path = Path(tempfile.mkdtemp(prefix="refactor-review-"))
        branch_created = False

        try:
            self._run_git(
                repo_root,
                "worktree",
                "add",
                "-b",
                review_branch_name,
                str(worktree_path),
                start_ref,
            )
            branch_created = True

            applied_patches = self._refactor_executor.apply(patches, str(worktree_path))
            committed_files = tuple(
                sorted(
                    {
                        patch.file_path.as_posix()
                        for patch in applied_patches
                        if patch.status == RefactorStatus.APPLIED
                    }
                )
            )
            if not committed_files:
                raise RuntimeError(
                    "No approved refactor patches could be applied in the review branch worktree."
                )

            self._run_git(worktree_path, "add", "--", *committed_files)
            self._run_git(worktree_path, "commit", "-m", self._commit_message)
            commit_sha = self._run_git(worktree_path, "rev-parse", "HEAD").strip()

            remote_ref = None
            if push:
                self._run_git(worktree_path, "push", "-u", remote_name, review_branch_name)
                remote_ref = f"{remote_name}/{review_branch_name}"

            return ReviewBranchMaterialization(
                branch_name=review_branch_name,
                commit_sha=commit_sha,
                pushed=push,
                remote_ref=remote_ref,
                committed_files=committed_files,
            )
        except Exception:
            if branch_created:
                self._safe_remove_worktree(repo_root, worktree_path)
                self._safe_delete_branch(repo_root, review_branch_name)
            else:
                shutil.rmtree(worktree_path, ignore_errors=True)
            raise
        finally:
            if branch_created:
                self._safe_remove_worktree(repo_root, worktree_path)
            else:
                shutil.rmtree(worktree_path, ignore_errors=True)

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

    def _safe_delete_branch(self, repo_root: Path, branch_name: str) -> None:
        subprocess.run(
            ["git", "branch", "-D", branch_name],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

    def _default_branch_name(self, start_ref: str) -> str:
        sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", start_ref).strip("-._") or "review"
        return f"{sanitized}_refactor"