from pathlib import Path
import subprocess

import pytest

from app.domain.entities.changed_file import ChangedFile
from app.domain.enums.change_type import ChangeType
from app.domain.enums.language import Language
from app.domain.enums.severity import Severity
from app.domain.enums.validation_status import ValidationStatus
from app.domain.value_objects.project_profile import ProjectProfile
from app.infrastructure.adapters.validation.profile_validation_runner_adapter import (
    ProfileValidationRunnerAdapter,
)


class TestProfileValidationRunnerAdapter:
    def test_builds_python_lint_and_coverage_checks(self, tmp_path: Path) -> None:
        adapter = ProfileValidationRunnerAdapter(python_coverage_fail_under=85)
        profile = ProjectProfile("python", "python", None, "pytest", True)
        changed_files = [
            ChangedFile(
                path=Path("tests/test_service.py"),
                change_type=ChangeType.MODIFIED,
                language=Language.PYTHON,
                diff_content="",
            )
        ]

        checks = adapter._build_checks(profile, tmp_path, changed_files)

        assert [check.code for check in checks] == ["LINT", "COVERAGE"]
        assert checks[0].command == ["ruff", "check", "tests/test_service.py"]
        assert checks[0].target == "tests/test_service.py"
        assert checks[1].command == ["pytest", "--cov=.", "--cov-fail-under=85", "-q", "tests/test_service.py"]
        assert checks[1].target == "tests/test_service.py"
        assert checks[1].working_directory == tmp_path

    def test_resolves_csharp_validation_directory_to_parent_of_src(self, tmp_path: Path) -> None:
        repo_path = tmp_path / "src"
        repo_path.mkdir()
        (tmp_path / "tests").mkdir()
        adapter = ProfileValidationRunnerAdapter()
        profile = ProjectProfile("csharp-aspnetcore", "csharp", "aspnetcore", None, True)
        changed_files = [
            ChangedFile(
                path=Path("src/Core/OrderService.cs"),
                change_type=ChangeType.MODIFIED,
                language=Language.CSHARP,
                diff_content="",
            )
        ]

        checks = adapter._build_checks(profile, repo_path, changed_files)

        assert checks[0].command == [
            "dotnet",
            "format",
            "--verify-no-changes",
            "--verbosity",
            "minimal",
            "--include",
            "src/Core/OrderService.cs",
        ]
        assert checks[0].target == "src/Core/OrderService.cs"
        assert checks[1].command == ["dotnet", "test", "--nologo", "--verbosity", "minimal"]
        assert checks[1].fallback_used is True
        assert checks[1].working_directory == tmp_path

    def test_targets_csharp_validation_by_owner_project_and_related_test_project(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src" / "Orders"
        src_dir.mkdir(parents=True)
        tests_dir = tmp_path / "tests" / "Orders.Tests"
        tests_dir.mkdir(parents=True)
        (src_dir / "Orders.csproj").write_text("<Project />", encoding="utf-8")
        (tests_dir / "Orders.Tests.csproj").write_text("<Project />", encoding="utf-8")

        adapter = ProfileValidationRunnerAdapter()
        profile = ProjectProfile("csharp-aspnetcore", "csharp", "aspnetcore", None, True)
        changed_files = [
            ChangedFile(
                path=Path("src/Orders/OrderService.cs"),
                change_type=ChangeType.MODIFIED,
                language=Language.CSHARP,
                diff_content="",
            )
        ]

        checks = adapter._build_checks(profile, src_dir.parent, changed_files)

        assert checks[0].command == [
            "dotnet",
            "format",
            "src/Orders/Orders.csproj",
            "--verify-no-changes",
            "--verbosity",
            "minimal",
        ]
        assert checks[0].target == "project:Orders"
        assert checks[1].command == [
            "dotnet",
            "test",
            "tests/Orders.Tests/Orders.Tests.csproj",
            "--nologo",
            "--verbosity",
            "minimal",
        ]
        assert checks[1].target == "test-project:Orders.Tests"

    def test_builds_angular_targeted_lint_and_test_checks(self, tmp_path: Path) -> None:
        node_bin = tmp_path / "node_modules" / ".bin"
        node_bin.mkdir(parents=True)
        (node_bin / "eslint.cmd").write_text("", encoding="utf-8")
        component_dir = tmp_path / "src" / "app"
        spec_path = component_dir / "users.component.spec.ts"
        spec_path.parent.mkdir(parents=True)
        (component_dir / "users.component.ts").write_text("export class UsersComponent {}", encoding="utf-8")
        spec_path.write_text("describe('users', () => {});", encoding="utf-8")
        (component_dir / "users.component.html").write_text("<div></div>", encoding="utf-8")
        (component_dir / "users.component.scss").write_text(".users {}", encoding="utf-8")

        adapter = ProfileValidationRunnerAdapter()
        profile = ProjectProfile("typescript-angular", "typescript", "angular", "karma", True)
        changed_files = [
            ChangedFile(
                path=Path("src/app/users.component.ts"),
                change_type=ChangeType.MODIFIED,
                language=Language.TYPESCRIPT,
                diff_content="",
            )
        ]

        checks = adapter._build_checks(profile, tmp_path, changed_files)

        assert checks[0].command == [
            str(node_bin / "eslint.cmd"),
            "src/app/users.component.html",
            "src/app/users.component.scss",
            "src/app/users.component.ts",
        ]
        assert checks[0].target == "module:src/app/users.component"
        assert checks[1].command == [
            "npm",
            "run",
            "test",
            "--",
            "--watch=false",
            "--include",
            "src/app/users.component.spec.ts",
        ]
        assert checks[1].target == "module:src/app/users.component"

    def test_returns_error_when_validation_tool_is_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        adapter = ProfileValidationRunnerAdapter()
        profile = ProjectProfile("python", "python", None, "pytest", True)

        def _raise(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            raise AssertionError("subprocess.run should not be called in plan-only mode")

        monkeypatch.setattr(subprocess, "run", _raise)

        result = adapter.validate(str(tmp_path), profile, [])

        assert result.passed is False
        assert result.status == ValidationStatus.SKIPPED
        assert result.issues == []
        assert result.executed_checks == []
        assert result.planned_checks == [
            "LINT:repo-wide [fallback] -> ruff check .",
            "COVERAGE:repo-wide [fallback] -> pytest --cov=. --cov-fail-under=80 -q",
        ]

    def test_returns_failure_when_command_exits_non_zero(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        adapter = ProfileValidationRunnerAdapter(execution_enabled=True)
        profile = ProjectProfile("python", "python", None, "pytest", True)

        def _run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            command = args[0]
            if command == ["ruff", "check", "."]:
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")
            return subprocess.CompletedProcess(args=command, returncode=1, stdout="", stderr="coverage below threshold")

        monkeypatch.setattr(
            subprocess,
            "run",
            _run,
        )

        result = adapter.validate(str(tmp_path), profile, [])

        assert result.passed is False
        assert result.status == ValidationStatus.UNSAFE
        assert result.issues[0].code == "COVERAGE_FAILED"
        assert result.executed_checks == [
            "LINT:repo-wide [fallback] -> ruff check .",
            "COVERAGE:repo-wide [fallback] -> pytest --cov=. --cov-fail-under=80 -q",
        ]

    def test_returns_success_when_command_passes(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        adapter = ProfileValidationRunnerAdapter(execution_enabled=True)
        profile = ProjectProfile("python", "python", None, "pytest", True)

        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *args, **kwargs: subprocess.CompletedProcess(args=["pytest", "-q"], returncode=0, stdout="ok", stderr=""),
        )

        result = adapter.validate(str(tmp_path), profile, [])

        assert result.passed is True
        assert result.status == ValidationStatus.SAFE
        assert result.executed_checks == [
            "LINT:repo-wide [fallback] -> ruff check .",
            "COVERAGE:repo-wide [fallback] -> pytest --cov=. --cov-fail-under=80 -q",
        ]