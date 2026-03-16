import re
from pathlib import Path

from app.domain.entities.changed_file import ChangedFile
from app.domain.enums.change_type import ChangeType
from app.domain.enums.language import Language
from app.domain.value_objects.impact_target_resolution import ImpactTargetResolution

_C_SHARP_TEST_PROJECT_RE = re.compile(r"test|tests", re.IGNORECASE)
_CSHARP_PROJECT_SUFFIX = ".csproj"


class CSharpImpactTargetResolverAdapter:
    """Resolve C# project, lint, and test targets from the changed scope."""

    def resolve(
        self,
        repo_path: Path,
        changed_files: list[ChangedFile],
    ) -> ImpactTargetResolution:
        working_directory = self._resolve_csharp_directory(repo_path)
        owner_projects = self._resolve_owner_projects(working_directory, changed_files)
        lint_targets = []
        if not owner_projects:
            lint_targets = self._resolve_relative_paths(
                changed_files,
                allowed_languages={Language.CSHARP, Language.XML, Language.CONFIG},
                working_directory=working_directory,
            )
        test_targets = self._resolve_test_targets(working_directory, changed_files, owner_projects)
        return ImpactTargetResolution(
            working_directory=working_directory,
            lint_targets=lint_targets,
            test_targets=test_targets,
            owner_projects=[project.as_posix() for project in owner_projects],
        )

    def _resolve_relative_paths(
        self,
        changed_files: list[ChangedFile],
        allowed_languages: set[Language],
        working_directory: Path,
    ) -> list[str]:
        targets: set[str] = set()
        for changed_file in changed_files:
            if changed_file.change_type == ChangeType.DELETED:
                continue
            if changed_file.language not in allowed_languages:
                continue
            try:
                relative_path = (working_directory / changed_file.path).relative_to(working_directory)
            except ValueError:
                continue
            targets.add(relative_path.as_posix())
        return sorted(targets)

    def _resolve_owner_projects(
        self,
        working_directory: Path,
        changed_files: list[ChangedFile],
    ) -> list[Path]:
        owner_projects: set[Path] = set()
        for changed_file in changed_files:
            if changed_file.change_type == ChangeType.DELETED:
                continue
            if changed_file.language not in {Language.CSHARP, Language.XML, Language.CONFIG} and changed_file.path.suffix.lower() != _CSHARP_PROJECT_SUFFIX:
                continue

            if changed_file.path.suffix.lower() == _CSHARP_PROJECT_SUFFIX:
                owner_projects.add(Path(changed_file.path.as_posix()))
                continue

            project_file = self._find_nearest_csproj(working_directory / changed_file.path)
            if project_file is not None:
                owner_projects.add(project_file.relative_to(working_directory))

        return sorted(owner_projects)

    def _resolve_test_targets(
        self,
        working_directory: Path,
        changed_files: list[ChangedFile],
        owner_projects: list[Path],
    ) -> list[str]:
        related_test_projects = self._resolve_related_test_projects(working_directory, owner_projects)
        if related_test_projects:
            return sorted(project.as_posix() for project in related_test_projects)

        targets: set[str] = set()
        for changed_file in changed_files:
            if changed_file.change_type == ChangeType.DELETED:
                continue

            if changed_file.path.suffix.lower() == _CSHARP_PROJECT_SUFFIX and _C_SHARP_TEST_PROJECT_RE.search(changed_file.path.name):
                targets.add(changed_file.path.as_posix())
                continue

            if not self._looks_like_test_file(changed_file.path):
                continue

            project_file = self._find_nearest_csproj(working_directory / changed_file.path)
            if project_file is not None:
                targets.add(project_file.relative_to(working_directory).as_posix())

        return sorted(targets)

    def _resolve_related_test_projects(
        self,
        working_directory: Path,
        owner_projects: list[Path],
    ) -> list[Path]:
        if not owner_projects:
            return []

        all_projects = list(working_directory.rglob("*.csproj"))
        related: set[Path] = set()
        for owner_project in owner_projects:
            owner_stem = owner_project.stem.lower()
            for project in all_projects:
                relative_project = project.relative_to(working_directory)
                if not _C_SHARP_TEST_PROJECT_RE.search(relative_project.name):
                    continue
                project_stem = relative_project.stem.lower()
                if owner_stem in project_stem or project_stem in owner_stem:
                    related.add(relative_project)
        return sorted(related)

    def _resolve_csharp_directory(self, repo_path: Path) -> Path:
        if repo_path.name.lower() == "src" and (repo_path.parent / "tests").exists():
            return repo_path.parent

        current = repo_path
        while current != current.parent:
            if any(current.glob("*.sln")):
                return current
            current = current.parent
        return repo_path

    def _looks_like_test_file(self, path: Path) -> bool:
        normalized = path.as_posix().lower()
        return "/tests/" in normalized or normalized.endswith("tests.cs") or normalized.endswith("test.cs")

    def _find_nearest_csproj(self, absolute_path: Path) -> Path | None:
        current = absolute_path.parent
        while current != current.parent:
            csproj_files = list(current.glob("*.csproj"))
            if csproj_files:
                return csproj_files[0]
            current = current.parent
        return None