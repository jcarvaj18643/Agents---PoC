import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.application.ports.outbound.impact_target_resolver_port import (
    ImpactTargetResolverPort,
)
from app.application.ports.outbound.validation_runner_port import ValidationRunnerPort
from app.domain.entities.changed_file import ChangedFile
from app.domain.enums.severity import Severity
from app.domain.value_objects.impact_target_resolution import ImpactTargetResolution
from app.domain.value_objects.project_profile import ProjectProfile
from app.domain.value_objects.validation_result import ValidationIssue, ValidationResult
from app.infrastructure.adapters.validation.profile_impact_target_resolver_adapter import (
    ProfileImpactTargetResolverAdapter,
)
from app.infrastructure.logging.console_logger import get_logger

logger = get_logger(__name__)


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
        impact_target_resolver: ImpactTargetResolverPort | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._lint_enabled = lint_enabled
        self._coverage_enabled = coverage_enabled
        self._execution_enabled = execution_enabled
        self._python_coverage_fail_under = python_coverage_fail_under
        self._impact_target_resolver = impact_target_resolver or ProfileImpactTargetResolverAdapter()

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
        resolution = self._impact_target_resolver.resolve(
            str(repo_path),
            profile,
            changed_files,
        )
        return self._build_checks_for_resolution(profile, resolution)

    def _build_checks_for_resolution(
        self,
        profile: ProjectProfile,
        resolution: ImpactTargetResolution,
    ) -> list[ValidationCheck]:
        if profile.language == "python":
            return self._build_python_checks(resolution)
        if profile.language == "csharp":
            return self._build_csharp_checks(resolution)
        if profile.language == "typescript" and profile.framework == "angular":
            return self._build_angular_checks(resolution)
        return []

    def _build_python_checks(
        self,
        resolution: ImpactTargetResolution,
    ) -> list[ValidationCheck]:
        checks: list[ValidationCheck] = []
        lint_targets = resolution.lint_targets
        test_targets = resolution.test_targets

        if self._lint_enabled:
            checks.append(
                ValidationCheck(
                    code="LINT",
                    command=["ruff", "check", *(lint_targets or ["."])],
                    working_directory=resolution.working_directory,
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
                    working_directory=resolution.working_directory,
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
                    working_directory=resolution.working_directory,
                    description="tests",
                    target=", ".join(test_targets) if test_targets else "repo-wide",
                    fallback_used=not bool(test_targets),
                )
            )
        return checks

    def _build_csharp_checks(
        self,
        resolution: ImpactTargetResolution,
    ) -> list[ValidationCheck]:
        checks = self._build_csharp_lint_checks(resolution)
        checks += self._build_csharp_test_checks(resolution)
        return checks

    def _build_csharp_lint_checks(
        self,
        resolution: ImpactTargetResolution,
    ) -> list[ValidationCheck]:
        if not self._lint_enabled:
            return []

        if resolution.owner_projects:
            return [
                ValidationCheck(
                    code="LINT",
                    command=[
                        "dotnet",
                        "format",
                        owner_project,
                        "--verify-no-changes",
                        "--verbosity",
                        "minimal",
                    ],
                    working_directory=resolution.working_directory,
                    description=f"lint[{Path(owner_project).stem}]",
                    target=f"project:{Path(owner_project).stem}",
                )
                for owner_project in resolution.owner_projects
            ]

        lint_targets = resolution.lint_targets
        lint_command = ["dotnet", "format", "--verify-no-changes", "--verbosity", "minimal"]
        if lint_targets:
            lint_command.extend(["--include", *lint_targets])
        return [
            ValidationCheck(
                code="LINT",
                command=lint_command,
                working_directory=resolution.working_directory,
                description="lint",
                target=", ".join(lint_targets) if lint_targets else "repo-wide",
                fallback_used=not bool(lint_targets),
            )
        ]

    def _build_csharp_test_checks(
        self,
        resolution: ImpactTargetResolution,
    ) -> list[ValidationCheck]:
        test_targets = resolution.test_targets
        if test_targets:
            return [
                ValidationCheck(
                    code="TEST",
                    command=["dotnet", "test", test_target, "--nologo", "--verbosity", "minimal"],
                    working_directory=resolution.working_directory,
                    description=f"tests[{test_target}]",
                    target=f"test-project:{Path(test_target).stem}",
                )
                for test_target in test_targets
            ]

        return [
            ValidationCheck(
                code="TEST",
                command=["dotnet", "test", "--nologo", "--verbosity", "minimal"],
                working_directory=resolution.working_directory,
                description="tests",
                target="repo-wide",
                fallback_used=True,
            )
        ]

    def _build_angular_checks(
        self,
        resolution: ImpactTargetResolution,
    ) -> list[ValidationCheck]:
        checks: list[ValidationCheck] = []
        if self._lint_enabled:
            checks.append(self._build_angular_lint_check(resolution))

        test_targets = resolution.test_targets
        test_command = ["npm", "run", "test", "--", "--watch=false"]
        for test_target in test_targets:
            test_command.extend(["--include", test_target])
        target_label = self._resolve_angular_target_label(resolution.module_owners, test_targets)
        checks.append(
            ValidationCheck(
                code="TEST",
                command=test_command,
                working_directory=resolution.working_directory,
                description="tests",
                target=target_label,
                fallback_used=not bool(test_targets),
            )
        )
        return checks

    def _build_angular_lint_check(
        self,
        resolution: ImpactTargetResolution,
    ) -> ValidationCheck:
        eslint_command = self._resolve_angular_eslint_command(resolution.working_directory)
        lint_targets = resolution.lint_targets
        if eslint_command and lint_targets:
            return ValidationCheck(
                code="LINT",
                command=[eslint_command, *lint_targets],
                working_directory=resolution.working_directory,
                description="lint",
                target=", ".join(f"module:{owner}" for owner in resolution.module_owners) if resolution.module_owners else ", ".join(lint_targets),
            )

        return ValidationCheck(
            code="LINT",
            command=["npm", "run", "lint"],
            working_directory=resolution.working_directory,
            description="lint",
            target="repo-wide",
            fallback_used=True,
        )

    def _resolve_angular_eslint_command(self, repo_path: Path) -> str | None:
        for candidate in (
            repo_path / "node_modules" / ".bin" / "eslint.cmd",
            repo_path / "node_modules" / ".bin" / "eslint",
        ):
            if candidate.exists():
                return str(candidate)
        return None

    def _resolve_angular_target_label(self, module_owners: list[str], test_targets: list[str]) -> str:
        if module_owners:
            return ", ".join(f"module:{owner}" for owner in module_owners)
        if test_targets:
            return ", ".join(test_targets)
        return "repo-wide"

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

    def _summarize_output(self, stdout: str, stderr: str) -> str:
        combined = (stderr or stdout).strip()
        if not combined:
            return "No diagnostic output was produced."
        first_line = combined.splitlines()[0].strip()
        if len(first_line) > 240:
            return first_line[:240] + "..."
        return first_line