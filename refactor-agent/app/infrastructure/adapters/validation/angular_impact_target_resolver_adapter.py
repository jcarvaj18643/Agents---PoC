from pathlib import Path

from app.domain.entities.changed_file import ChangedFile
from app.domain.enums.change_type import ChangeType
from app.domain.enums.language import Language
from app.domain.value_objects.impact_target_resolution import ImpactTargetResolution

_ANGULAR_SPEC_SUFFIX = ".spec.ts"
_ANGULAR_CODE_SUFFIXES = (".component", ".service", ".directive", ".pipe", ".guard", ".resolver", ".store")


class AngularImpactTargetResolverAdapter:
    """Resolve Angular module companions and spec targets from the changed scope."""

    def resolve(
        self,
        repo_path: Path,
        changed_files: list[ChangedFile],
    ) -> ImpactTargetResolution:
        module_owners = self._resolve_module_owners(changed_files)
        lint_targets = self._resolve_lint_targets(repo_path, changed_files, module_owners)
        test_targets = self._resolve_test_targets(repo_path, changed_files, module_owners)
        return ImpactTargetResolution(
            working_directory=repo_path,
            lint_targets=lint_targets,
            test_targets=test_targets,
            module_owners=module_owners,
        )

    def _resolve_module_owners(self, changed_files: list[ChangedFile]) -> list[str]:
        owners: set[str] = set()
        for changed_file in changed_files:
            if changed_file.change_type == ChangeType.DELETED:
                continue
            owner = self._resolve_owner(changed_file)
            if owner:
                owners.add(owner)
        return sorted(owners)

    def _resolve_owner(self, changed_file: ChangedFile) -> str | None:
        stem = changed_file.path.as_posix()
        for suffix in (".ts", ".html", ".scss", ".css"):
            if stem.endswith(suffix):
                stem = stem[: -len(suffix)]
                break

        for angular_suffix in _ANGULAR_CODE_SUFFIXES:
            if stem.endswith(angular_suffix):
                return stem

        if changed_file.impacted_symbol and "." in changed_file.impacted_symbol.name:
            return stem

        if changed_file.language in {Language.TYPESCRIPT, Language.HTML, Language.SCSS}:
            return stem
        return None

    def _resolve_lint_targets(
        self,
        repo_path: Path,
        changed_files: list[ChangedFile],
        module_owners: list[str],
    ) -> list[str]:
        if module_owners:
            targets: set[str] = set()
            for owner in module_owners:
                targets.update(self._resolve_owner_companion_files(repo_path, owner))
            return sorted(targets)

        return self._resolve_relative_paths(
            changed_files,
            allowed_languages={Language.TYPESCRIPT, Language.HTML, Language.SCSS},
        )

    def _resolve_test_targets(
        self,
        repo_path: Path,
        changed_files: list[ChangedFile],
        module_owners: list[str],
    ) -> list[str]:
        owner_targets: set[str] = set()
        for owner in module_owners:
            spec_candidate = Path(f"{owner}{_ANGULAR_SPEC_SUFFIX}")
            if (repo_path / spec_candidate).exists():
                owner_targets.add(spec_candidate.as_posix())
        if owner_targets:
            return sorted(owner_targets)

        changed_spec_files = [
            changed_file.path.as_posix()
            for changed_file in changed_files
            if changed_file.change_type != ChangeType.DELETED
            and changed_file.path.suffix.lower() == ".ts"
            and changed_file.path.name.endswith(_ANGULAR_SPEC_SUFFIX)
        ]
        if changed_spec_files:
            return changed_spec_files

        candidate_paths: set[str] = set()
        for changed_file in changed_files:
            if changed_file.change_type == ChangeType.DELETED or changed_file.language != Language.TYPESCRIPT:
                continue
            if changed_file.path.name.endswith(_ANGULAR_SPEC_SUFFIX):
                continue
            spec_candidate = changed_file.path.with_name(changed_file.path.stem + _ANGULAR_SPEC_SUFFIX)
            if (repo_path / spec_candidate).exists():
                candidate_paths.add(spec_candidate.as_posix())
        return sorted(candidate_paths)

    def _resolve_owner_companion_files(self, repo_path: Path, owner: str) -> set[str]:
        targets: set[str] = set()
        for suffix in (".ts", ".html", ".scss", ".css"):
            candidate = Path(f"{owner}{suffix}")
            if (repo_path / candidate).exists():
                targets.add(candidate.as_posix())
        return targets

    def _resolve_relative_paths(
        self,
        changed_files: list[ChangedFile],
        allowed_languages: set[Language],
    ) -> list[str]:
        targets: set[str] = set()
        for changed_file in changed_files:
            if changed_file.change_type == ChangeType.DELETED:
                continue
            if changed_file.language not in allowed_languages:
                continue
            targets.add(changed_file.path.as_posix())
        return sorted(targets)