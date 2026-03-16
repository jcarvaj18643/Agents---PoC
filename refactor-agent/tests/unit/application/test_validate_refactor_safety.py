from pathlib import Path

from app.application.policies.refactor_safety_policy import RefactorSafetyPolicy
from app.application.use_cases.validate_refactor_safety import ValidateRefactorSafetyUseCase
from app.domain.entities.changed_file import ChangedFile
from app.domain.enums.change_type import ChangeType
from app.domain.enums.language import Language
from app.domain.enums.severity import Severity
from app.domain.enums.validation_status import ValidationStatus
from app.domain.value_objects.project_profile import ProjectProfile
from app.domain.value_objects.validation_result import ValidationIssue, ValidationResult


class _FakeValidationRunner:
    def __init__(self, result: ValidationResult) -> None:
        self._result = result
        self.calls: list[tuple[str, str, list[str]]] = []

    def validate(self, repo_path: str, profile: ProjectProfile, changed_files: list[ChangedFile]) -> ValidationResult:
        self.calls.append((repo_path, profile.name, [changed_file.path.as_posix() for changed_file in changed_files]))
        return self._result


class TestValidateRefactorSafetyUseCase:
    def test_uses_profile_validation_runner_when_policy_passes(self) -> None:
        runner = _FakeValidationRunner(ValidationResult.safe())
        profile = ProjectProfile(
            name="python",
            language="python",
            framework=None,
            test_framework="pytest",
            has_type_hints=True,
        )
        use_case = ValidateRefactorSafetyUseCase(
            safety_policy=RefactorSafetyPolicy(),
            validation_runner=runner,
        )

        result = use_case.execute([], [], "/repo", profile)

        assert result.passed is True
        assert result.status == ValidationStatus.SAFE
        assert runner.calls == [("/repo", "python", [])]

    def test_returns_policy_failure_without_running_external_validation(self) -> None:
        runner = _FakeValidationRunner(ValidationResult.safe())
        profile = ProjectProfile(
            name="python",
            language="python",
            framework=None,
            test_framework="pytest",
            has_type_hints=True,
        )
        policy = RefactorSafetyPolicy(max_suggestions_per_run=0)
        use_case = ValidateRefactorSafetyUseCase(
            safety_policy=policy,
            validation_runner=runner,
        )

        result = use_case.execute([object()], [], "/repo", profile)  # type: ignore[list-item]

        assert result.passed is False
        assert result.status == ValidationStatus.REFUSED
        assert result.issues[0].severity == Severity.WARNING
        assert runner.calls == []

    def test_refuses_when_changed_scope_touches_public_api_surface(self) -> None:
        runner = _FakeValidationRunner(ValidationResult.safe())
        profile = ProjectProfile(
            name="csharp-aspnetcore",
            language="csharp",
            framework="aspnetcore",
            test_framework="xunit",
            has_type_hints=True,
        )
        changed_files = [
            ChangedFile(
                path=Path("Core/Abstractions/IOrderReader.cs"),
                change_type=ChangeType.MODIFIED,
                language=Language.CSHARP,
                diff_content="+public interface IOrderReader { }\n",
            )
        ]
        use_case = ValidateRefactorSafetyUseCase(
            safety_policy=RefactorSafetyPolicy(),
            validation_runner=runner,
        )

        result = use_case.execute([], changed_files, "/repo", profile)

        assert result.passed is False
        assert result.status == ValidationStatus.REFUSED
        assert result.issues[0].code == "POLICY_PUBLIC_API_REVIEW_REQUIRED"
        assert runner.calls == []

    def test_ignores_python_test_files_for_public_api_gate(self) -> None:
        runner = _FakeValidationRunner(ValidationResult.safe())
        profile = ProjectProfile(
            name="python",
            language="python",
            framework=None,
            test_framework="pytest",
            has_type_hints=True,
        )
        changed_files = [
            ChangedFile(
                path=Path("tests/test_public_contracts.py"),
                change_type=ChangeType.MODIFIED,
                language=Language.PYTHON,
                diff_content="+def test_public_contract() -> None:\n",
            )
        ]
        use_case = ValidateRefactorSafetyUseCase(
            safety_policy=RefactorSafetyPolicy(),
            validation_runner=runner,
        )

        result = use_case.execute([], changed_files, "/repo", profile)

        assert result.passed is True
        assert result.status == ValidationStatus.SAFE
        assert runner.calls == [("/repo", "python", ["tests/test_public_contracts.py"])]