import re
from pathlib import Path

from app.domain.entities.changed_file import ChangedFile
from app.domain.enums.change_type import ChangeType
from app.domain.enums.language import Language
from app.domain.value_objects.impact_target_resolution import ImpactTargetResolution

_PYTHON_TEST_FILE_RE = re.compile(r"(^|/)(test_[^/]+\.py|[^/]+_test\.py)$")


class PythonImpactTargetResolverAdapter:
    """Resolve Python lint and test targets from the changed scope."""

    def resolve(
        self,
        repo_path: Path,
        changed_files: list[ChangedFile],
    ) -> ImpactTargetResolution:
        lint_targets = self._resolve_relative_paths(changed_files)
        test_targets = self._resolve_test_targets(repo_path, changed_files, lint_targets)
        return ImpactTargetResolution(
            working_directory=repo_path,
            lint_targets=lint_targets,
            test_targets=test_targets,
        )

    def _resolve_test_targets(
        self,
        repo_path: Path,
        changed_files: list[ChangedFile],
        lint_targets: list[str],
    ) -> list[str]:
        changed_test_files = [path for path in lint_targets if _PYTHON_TEST_FILE_RE.search(path)]
        if changed_test_files:
            return changed_test_files

        candidate_paths: set[str] = set()
        for changed_file in changed_files:
            if changed_file.change_type == ChangeType.DELETED or changed_file.language != Language.PYTHON:
                continue

            source_path = changed_file.path
            if _PYTHON_TEST_FILE_RE.search(source_path.as_posix()):
                continue

            stem = source_path.stem
            candidates = (
                source_path.parent / f"test_{stem}.py",
                Path("tests") / source_path.parent / f"test_{stem}.py",
                Path("tests") / f"test_{stem}.py",
            )
            for candidate in candidates:
                if (repo_path / candidate).exists():
                    candidate_paths.add(candidate.as_posix())

        return sorted(candidate_paths)

    def _resolve_relative_paths(self, changed_files: list[ChangedFile]) -> list[str]:
        targets: set[str] = set()
        for changed_file in changed_files:
            if changed_file.change_type == ChangeType.DELETED:
                continue
            if changed_file.language != Language.PYTHON:
                continue
            targets.add(changed_file.path.as_posix())
        return sorted(targets)