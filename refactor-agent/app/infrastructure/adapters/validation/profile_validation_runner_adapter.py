import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.application.ports.outbound.validation_runner_port import ValidationRunnerPort
from app.domain.entities.changed_file import ChangedFile
from app.domain.enums.change_type import ChangeType
from app.domain.enums.language import Language
from app.domain.enums.severity import Severity
from app.domain.value_objects.project_profile import ProjectProfile
from app.domain.value_objects.validation_result import ValidationIssue, ValidationResult
from app.infrastructure.logging.console_logger import get_logger

logger = get_logger(__name__)

_PYTHON_TEST_FILE_RE = re.compile(r"(^|/)(test_[^/]+\.py|[^/]+_test\.py)$")
_C_SHARP_TEST_PROJECT_RE = re.compile(r"test|tests", re.IGNORECASE)
_ANGULAR_SPEC_SUFFIX = ".spec.ts"
_ANGULAR_CODE_SUFFIXES = (".component", ".service", ".directive", ".pipe", ".guard", ".resolver", ".store")
_CSHARP_PROJECT_SUFFIX = ".csproj"


@dataclass(frozen=True)
class ValidationCheck:
    code: str
    command: list[str]
    working_directory: Path
    description: str
    target: str
    fallback_used: bool = False


class ProfileValidationRunnerAdapter(ValidationRunnerPort):
    """Builds stack-specific validation plans for the detected project profile.

    By default the adapter is non-intrusive: it reports the exact commands that
    CI/CD should run, but it does not execute them against the target repo.
    """

    def __init__(
        self,
        timeout_seconds: int = 600,
        lint_enabled: bool = True,
        coverage_enabled: bool = True,
        execution_enabled: bool = False,
        python_coverage_fail_under: int = 80,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._lint_enabled = lint_enabled
        self._coverage_enabled = coverage_enabled
        self._execution_enabled = execution_enabled
        self._python_coverage_fail_under = python_coverage_fail_under

    def validate(
        self,
        repo_path: str,
        profile: ProjectProfile,
        changed_files: list[ChangedFile],
    ) -> ValidationResult:
        checks = self._build_checks(profile, Path(repo_path), changed_files)
        if not checks:
            return ValidationResult.safe(summary="No validation plan was required for the detected profile.")

        planned_checks = [self._describe_check(check) for check in checks]
        if not self._execution_enabled:
            logger.info(
                "Validation deferred to CI/CD for profile '%s' with %d planned check(s)",
                profile.name,
                len(planned_checks),
            )
            return ValidationResult.skipped(
                planned_checks=planned_checks,
                summary="Validation was intentionally deferred to CI/CD; the agent did not execute commands in the target repository.",
            )

        issues: list[ValidationIssue] = []
        executed_checks = planned_checks
        for check in checks:
            logger.info(
                "Running %s validation for profile '%s': %s [cwd=%s]",
                check.description,
                profile.name,
                " ".join(check.command),
                check.working_directory,
            )
            issue = self._run_check(check)
            if issue is not None:
                issues.append(issue)

        if issues:
            return ValidationResult.unsafe(issues=issues, executed_checks=executed_checks)
        return ValidationResult.safe(executed_checks=executed_checks)

    def _build_checks(
        self,
        profile: ProjectProfile,
        repo_path: Path,
        changed_files: list[ChangedFile],
    ) -> list[ValidationCheck]:
        if profile.language == "python":
            return self._build_python_checks(repo_path, changed_files)
        if profile.language == "csharp":
            return self._build_csharp_checks(repo_path, changed_files)
        if profile.language == "typescript" and profile.framework == "angular":
            return self._build_angular_checks(repo_path, changed_files)
        return []

    def _build_python_checks(
        self,
        repo_path: Path,
        changed_files: list[ChangedFile],
    ) -> list[ValidationCheck]:
        checks: list[ValidationCheck] = []
        lint_targets = self._resolve_python_lint_targets(changed_files)
        test_targets = self._resolve_python_test_targets(repo_path, changed_files)

        if self._lint_enabled:
            checks.append(
                ValidationCheck(
                    code="LINT",
                    command=["ruff", "check", *(lint_targets or ["."])],
                    working_directory=repo_path,
                    description="lint",
                    target=", ".join(lint_targets) if lint_targets else "repo-wide",
                    fallback_used=not bool(lint_targets),
                )
            )
        if self._coverage_enabled:
            coverage_command = [
                "pytest",
                "--cov=.",
                f"--cov-fail-under={self._python_coverage_fail_under}",
                "-q",
            ]
            if test_targets:
                coverage_command.extend(test_targets)
            checks.append(
                ValidationCheck(
                    code="COVERAGE",
                    command=coverage_command,
                    working_directory=repo_path,
                    description="coverage",
                    target=", ".join(test_targets) if test_targets else "repo-wide",
                    fallback_used=not bool(test_targets),
                )
            )
        else:
            test_command = ["pytest", "-q"]
            if test_targets:
                test_command.extend(test_targets)
            checks.append(
                ValidationCheck(
                    code="TEST",
                    command=test_command,
                    working_directory=repo_path,
                    description="tests",
                    target=", ".join(test_targets) if test_targets else "repo-wide",
                    fallback_used=not bool(test_targets),
                )
            )
        return checks

    def _build_csharp_checks(
        self,
        repo_path: Path,
        changed_files: list[ChangedFile],
    ) -> list[ValidationCheck]:
        working_directory = self._resolve_csharp_directory(repo_path)
        owner_projects = self._resolve_csharp_owner_projects(working_directory, changed_files)
        checks = self._build_csharp_lint_checks(working_directory, changed_files, owner_projects)
        checks += self._build_csharp_test_checks(working_directory, changed_files, owner_projects)
        return checks

    def _build_csharp_lint_checks(
        self,
        working_directory: Path,
        changed_files: list[ChangedFile],
        owner_projects: list[Path],
    ) -> list[ValidationCheck]:
        if not self._lint_enabled:
            return []

        if owner_projects:
            return [
                ValidationCheck(
                    code="LINT",
                    command=[
                        "dotnet",
                        "format",
                        owner_project.as_posix(),
                        "--verify-no-changes",
                        "--verbosity",
                        "minimal",
                    ],
                    working_directory=working_directory,
                    description=f"lint[{owner_project.stem}]",
                    target=f"project:{owner_project.stem}",
                )
                for owner_project in owner_projects
            ]

        lint_targets = self._resolve_csharp_lint_targets(working_directory, changed_files)
        lint_command = ["dotnet", "format", "--verify-no-changes", "--verbosity", "minimal"]
        if lint_targets:
            lint_command.extend(["--include", *lint_targets])
        return [
            ValidationCheck(
                code="LINT",
                command=lint_command,
                working_directory=working_directory,
                description="lint",
                target=", ".join(lint_targets) if lint_targets else "repo-wide",
                fallback_used=not bool(lint_targets),
            )
        ]

    def _build_csharp_test_checks(
        self,
        working_directory: Path,
        changed_files: list[ChangedFile],
        owner_projects: list[Path],
    ) -> list[ValidationCheck]:
        test_targets = self._resolve_csharp_test_targets(working_directory, changed_files, owner_projects)
        if test_targets:
            return [
                ValidationCheck(
                    code="TEST",
                    command=["dotnet", "test", test_target, "--nologo", "--verbosity", "minimal"],
                    working_directory=working_directory,
                    description=f"tests[{test_target}]",
                    target=f"test-project:{Path(test_target).stem}",
                )
                for test_target in test_targets
            ]

        return [
            ValidationCheck(
                code="TEST",
                command=["dotnet", "test", "--nologo", "--verbosity", "minimal"],
                working_directory=working_directory,
                description="tests",
                target="repo-wide",
                fallback_used=True,
            )
        ]

    def _build_angular_checks(
        self,
        repo_path: Path,
        changed_files: list[ChangedFile],
    ) -> list[ValidationCheck]:
        checks: list[ValidationCheck] = []
        module_owners = self._resolve_angular_module_owners(changed_files)
        if self._lint_enabled:
            checks.append(self._build_angular_lint_check(repo_path, changed_files, module_owners))

        test_targets = self._resolve_angular_test_targets(repo_path, changed_files, module_owners)
        test_command = ["npm", "run", "test", "--", "--watch=false"]
        for test_target in test_targets:
            test_command.extend(["--include", test_target])
        target_label = self._resolve_angular_target_label(module_owners, test_targets)
        checks.append(
            ValidationCheck(
                code="TEST",
                command=test_command,
                working_directory=repo_path,
                description="tests",
                target=target_label,
                fallback_used=not bool(test_targets),
            )
        )
        return checks

    def _build_angular_lint_check(
        self,
        repo_path: Path,
        changed_files: list[ChangedFile],
        module_owners: list[str],
    ) -> ValidationCheck:
        eslint_command = self._resolve_angular_eslint_command(repo_path)
        lint_targets = self._resolve_angular_lint_targets(repo_path, changed_files, module_owners)
        if eslint_command and lint_targets:
            return ValidationCheck(
                code="LINT",
                command=[eslint_command, *lint_targets],
                working_directory=repo_path,
                description="lint",
                target=", ".join(f"module:{owner}" for owner in module_owners) if module_owners else ", ".join(lint_targets),
            )

        return ValidationCheck(
            code="LINT",
            command=["npm", "run", "lint"],
            working_directory=repo_path,
            description="lint",
            target="repo-wide",
            fallback_used=True,
        )

    def _resolve_python_lint_targets(self, changed_files: list[ChangedFile]) -> list[str]:
        return self._resolve_relative_paths(changed_files, allowed_languages={Language.PYTHON})

    def _resolve_python_test_targets(
        self,
        repo_path: Path,
        changed_files: list[ChangedFile],
    ) -> list[str]:
        changed_test_files = [
            path
            for path in self._resolve_python_lint_targets(changed_files)
            if _PYTHON_TEST_FILE_RE.search(path)
        ]
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

    def _resolve_csharp_lint_targets(
        self,
        working_directory: Path,
        changed_files: list[ChangedFile],
    ) -> list[str]:
        return self._resolve_relative_paths(
            changed_files,
            allowed_languages={Language.CSHARP, Language.XML, Language.CONFIG},
            working_directory=working_directory,
        )

    def _resolve_csharp_test_targets(
        self,
        working_directory: Path,
        changed_files: list[ChangedFile],
        owner_projects: list[Path] | None = None,
    ) -> list[str]:
        related_test_projects = self._resolve_related_csharp_test_projects(
            working_directory,
            owner_projects or [],
        )
        if related_test_projects:
            return sorted(project.as_posix() for project in related_test_projects)

        targets: set[str] = set()
        for changed_file in changed_files:
            if changed_file.change_type == ChangeType.DELETED:
                continue

            if changed_file.path.suffix.lower() == _CSHARP_PROJECT_SUFFIX and _C_SHARP_TEST_PROJECT_RE.search(changed_file.path.name):
                targets.add(changed_file.path.as_posix())
                continue

            if not self._looks_like_csharp_test_file(changed_file.path):
                continue

            project_file = self._find_nearest_csproj(working_directory / changed_file.path)
            if project_file is not None:
                targets.add(project_file.relative_to(working_directory).as_posix())

        return sorted(targets)

    def _resolve_angular_lint_targets(
        self,
        repo_path: Path,
        changed_files: list[ChangedFile],
        module_owners: list[str],
    ) -> list[str]:
        if module_owners:
            targets: set[str] = set()
            for owner in module_owners:
                targets.update(self._resolve_angular_owner_companion_files(repo_path, owner))
            return sorted(targets)

        return self._resolve_relative_paths(
            changed_files,
            allowed_languages={Language.TYPESCRIPT, Language.HTML, Language.SCSS},
        )

    def _resolve_angular_test_targets(
        self,
        repo_path: Path,
        changed_files: list[ChangedFile],
        module_owners: list[str] | None = None,
    ) -> list[str]:
        owner_targets: set[str] = set()
        for owner in module_owners or []:
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

    def _resolve_angular_eslint_command(self, repo_path: Path) -> str | None:
        for candidate in (
            repo_path / "node_modules" / ".bin" / "eslint.cmd",
            repo_path / "node_modules" / ".bin" / "eslint",
        ):
            if candidate.exists():
                return str(candidate)
        return None

    def _resolve_relative_paths(
        self,
        changed_files: list[ChangedFile],
        allowed_languages: set[Language],
        working_directory: Path | None = None,
    ) -> list[str]:
        targets: set[str] = set()
        for changed_file in changed_files:
            if changed_file.change_type == ChangeType.DELETED:
                continue
            if changed_file.language not in allowed_languages:
                continue
            relative_path = changed_file.path
            if working_directory is not None:
                try:
                    relative_path = (working_directory / changed_file.path).relative_to(working_directory)
                except ValueError:
                    continue
            targets.add(relative_path.as_posix())
        return sorted(targets)

    def _resolve_csharp_owner_projects(
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

    def _resolve_related_csharp_test_projects(
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

    def _resolve_angular_module_owners(self, changed_files: list[ChangedFile]) -> list[str]:
        owners: set[str] = set()
        for changed_file in changed_files:
            if changed_file.change_type == ChangeType.DELETED:
                continue
            owner = self._resolve_angular_owner(changed_file)
            if owner:
                owners.add(owner)
        return sorted(owners)

    def _resolve_angular_owner(self, changed_file: ChangedFile) -> str | None:
        normalized = changed_file.path.as_posix()
        stem = normalized
        for suffix in (".ts", ".html", ".scss", ".css"):
            if stem.endswith(suffix):
                stem = stem[: -len(suffix)]
                break

        for angular_suffix in _ANGULAR_CODE_SUFFIXES:
            if stem.endswith(angular_suffix):
                return stem

        if changed_file.impacted_symbol and "." in changed_file.impacted_symbol.name:
            return stem

        return stem if changed_file.language in {Language.TYPESCRIPT, Language.HTML, Language.SCSS} else None

    def _resolve_angular_owner_companion_files(self, repo_path: Path, owner: str) -> set[str]:
        targets: set[str] = set()
        for suffix in (".ts", ".html", ".scss", ".css"):
            candidate = Path(f"{owner}{suffix}")
            if (repo_path / candidate).exists():
                targets.add(candidate.as_posix())
        return targets

    def _resolve_angular_target_label(self, module_owners: list[str], test_targets: list[str]) -> str:
        if module_owners:
            return ", ".join(f"module:{owner}" for owner in module_owners)
        if test_targets:
            return ", ".join(test_targets)
        return "repo-wide"

    def _looks_like_csharp_test_file(self, path: Path) -> bool:
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

    def _run_check(self, check: ValidationCheck) -> ValidationIssue | None:
        try:
            result = subprocess.run(
                check.command,
                cwd=check.working_directory,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=self._timeout_seconds,
            )
        except FileNotFoundError:
            return ValidationIssue(
                code=f"{check.code}_TOOL_MISSING",
                message=f"{check.description.capitalize()} tool not found: {check.command[0]}",
                severity=Severity.ERROR,
                file_path=str(check.working_directory),
            )
        except subprocess.TimeoutExpired:
            return ValidationIssue(
                code=f"{check.code}_TIMEOUT",
                message=f"{check.description.capitalize()} validation timed out after {self._timeout_seconds} seconds.",
                severity=Severity.ERROR,
                file_path=str(check.working_directory),
            )

        if result.returncode == 0:
            return None

        output = self._summarize_output(result.stdout, result.stderr)
        return ValidationIssue(
            code=f"{check.code}_FAILED",
            message=f"Command failed: {' '.join(check.command)}. {output}",
            severity=Severity.ERROR,
            file_path=str(check.working_directory),
        )

    def _describe_check(self, check: ValidationCheck) -> str:
        fallback_suffix = " [fallback]" if check.fallback_used else ""
        return f"{check.code}:{check.target}{fallback_suffix} -> {' '.join(check.command)}"

    def _resolve_csharp_directory(self, repo_path: Path) -> Path:
        if repo_path.name.lower() == "src" and (repo_path.parent / "tests").exists():
            return repo_path.parent

        current = repo_path
        while current != current.parent:
            if any(current.glob("*.sln")):
                return current
            current = current.parent
        return repo_path

    def _summarize_output(self, stdout: str, stderr: str) -> str:
        combined = (stderr or stdout).strip()
        if not combined:
            return "No diagnostic output was produced."
        first_line = combined.splitlines()[0].strip()
        if len(first_line) > 240:
            return first_line[:240] + "..."
        return first_line