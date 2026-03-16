from pathlib import Path

from app.application.ports.outbound.git_diff_reader_port import GitDiffReaderPort
from app.domain.entities.code_scope import CodeScope
from app.infrastructure.logging.console_logger import get_logger

logger = get_logger(__name__)

_EXCLUDED_DIRECTORIES = {
    "node_modules",
    "dist",
    "build",
    "vendor",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

_EXCLUDED_FILE_NAMES = {
    "package-lock.json",
    "poetry.lock",
    "yarn.lock",
    "pnpm-lock.yaml",
}

_EXCLUDED_SUFFIXES = {".pyc", ".min.js", ".min.css"}


class AnalyzeDiffScopeUseCase:
    """Use case: parse a git diff and produce a structured CodeScope.

    Single responsibility: translate diff coordinates into the domain aggregate
    that every subsequent step operates on. Validation and filtering will be
    added here as the project matures.
    """

    def __init__(self, diff_reader: GitDiffReaderPort) -> None:
        self._diff_reader = diff_reader

    def execute(self, base_ref: str, head_ref: str, repo_path: str) -> CodeScope:
        raw_scope = self._diff_reader.read_diff(base_ref, head_ref, repo_path)
        filtered_files = []

        for changed_file in raw_scope.changed_files:
            if self._is_excluded(changed_file.path):
                logger.info("Skipping excluded file from diff scope: %s", changed_file.path)
                continue
            filtered_files.append(changed_file)

        filtered_scope = CodeScope(
            changed_files=filtered_files,
            changed_symbols=list(raw_scope.changed_symbols),
            base_ref=raw_scope.base_ref,
            head_ref=raw_scope.head_ref,
        )
        if filtered_scope.is_empty:
            logger.info(
                "Diff scope is empty after parsing/filtering for %s..%s",
                base_ref,
                head_ref,
            )
        return filtered_scope

    def _is_excluded(self, path: Path) -> bool:
        if any(part in _EXCLUDED_DIRECTORIES for part in path.parts):
            return True
        if path.name in _EXCLUDED_FILE_NAMES:
            return True
        return any(str(path).endswith(suffix) for suffix in _EXCLUDED_SUFFIXES)
