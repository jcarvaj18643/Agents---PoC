import subprocess
from pathlib import Path
from typing import Iterable

from app.application.ports.outbound.git_diff_reader_port import GitDiffReaderPort
from app.domain.entities.changed_file import ChangedFile
from app.domain.entities.code_scope import CodeScope
from app.infrastructure.logging.console_logger import get_logger
from app.infrastructure.parsers.diff_parser import DiffParser

logger = get_logger(__name__)

WORKTREE_REF = "WORKTREE"


class GitDiffReaderAdapter(GitDiffReaderPort):
    """Adapter: reads a git diff by invoking the system `git` binary.

    Translates the raw diff text through DiffParser into a CodeScope.
    All subprocess concerns live here, out of the domain and application layers.
    """

    def __init__(self, diff_parser: DiffParser) -> None:
        self._diff_parser = diff_parser

    def read_diff(self, base_ref: str, head_ref: str, repo_path: str) -> CodeScope:
        logger.info("Reading diff: %s..%s in %s", base_ref, head_ref, repo_path)

        raw_diff = self._run_git_diff(base_ref=base_ref, head_ref=head_ref, repo_path=repo_path)
        changed_files = self._normalize_changed_files(
            self._diff_parser.parse(raw_diff),
            repo_path,
        )
        if not changed_files:
            logger.info("Git diff produced no changed files for %s..%s", base_ref, head_ref)
        return CodeScope(
            changed_files=changed_files,
            base_ref=base_ref,
            head_ref=head_ref,
        )

    def _run_git_diff(self, base_ref: str, head_ref: str, repo_path: str) -> str:
        command = self._build_git_diff_command(base_ref, head_ref)
        try:
            result = subprocess.run(
                command,
                cwd=repo_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("git executable not found on PATH") from exc

        if result.returncode != 0:
            stderr = result.stderr.strip() or "unknown git diff failure"
            raise RuntimeError(f"git diff failed: {stderr}")

        return result.stdout

    def _build_git_diff_command(self, base_ref: str, head_ref: str) -> list[str]:
        command = ["git", "diff"]
        if head_ref.upper() == WORKTREE_REF:
            command.append(base_ref)
        else:
            command.extend([base_ref, head_ref])
        command.extend(["--no-ext-diff", "--find-renames", "--unified=3"])
        return command

    def _normalize_changed_files(self, changed_files: Iterable[ChangedFile], repo_path: str) -> list[ChangedFile]:
        relative_repo_subpath = self._get_relative_repo_subpath(repo_path)
        if relative_repo_subpath is None:
            return list(changed_files)

        normalized_files: list[ChangedFile] = []
        for changed_file in changed_files:
            try:
                normalized_path = changed_file.path.relative_to(relative_repo_subpath)
            except ValueError:
                continue

            normalized_files.append(
                ChangedFile(
                    path=normalized_path,
                    change_type=changed_file.change_type,
                    language=changed_file.language,
                    diff_content=changed_file.diff_content,
                    added_lines=changed_file.added_lines,
                    removed_lines=changed_file.removed_lines,
                    changed_line_numbers=changed_file.changed_line_numbers,
                    context_snapshot=changed_file.context_snapshot,
                )
            )

        return normalized_files

    def _get_relative_repo_subpath(self, repo_path: str) -> Path | None:
        requested_path = Path(repo_path).resolve()
        git_root = Path(self._get_git_root(repo_path)).resolve()
        if requested_path == git_root:
            return None
        return requested_path.relative_to(git_root)

    def _get_git_root(self, repo_path: str) -> str:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip() or "unknown git root detection failure"
            raise RuntimeError(f"git rev-parse failed: {stderr}")
        return result.stdout.strip()
