from pathlib import Path

from app.application.use_cases.validate_review_branch import ValidateReviewBranchUseCase
from app.domain.entities.changed_file import ChangedFile
from app.domain.enums.change_type import ChangeType
from app.domain.enums.language import Language
from app.domain.value_objects.project_profile import ProjectProfile
from app.domain.value_objects.review_branch_materialization import (
    ReviewBranchMaterialization,
)
from app.domain.value_objects.validation_result import ValidationResult


class _FakeReviewBranchValidator:
    def __init__(self, result: ValidationResult) -> None:
        self._result = result
        self.calls: list[tuple[str, str, str, list[str]]] = []

    def validate(self, review_branch, repo_path, profile, changed_files):  # type: ignore[no-untyped-def]
        self.calls.append(
            (
                review_branch.branch_name,
                repo_path,
                profile.name,
                [changed_file.path.as_posix() for changed_file in changed_files],
            )
        )
        return self._result


class TestValidateReviewBranchUseCase:
    def test_skips_when_disabled(self) -> None:
        validator = _FakeReviewBranchValidator(ValidationResult.safe())
        use_case = ValidateReviewBranchUseCase(validator)  # type: ignore[arg-type]
        profile = ProjectProfile("python", "python", None, "pytest", True)

        result = use_case.execute(
            review_branch=ReviewBranchMaterialization(branch_name="feature_refactor", commit_sha="abc123"),
            repo_path="/repo",
            profile=profile,
            changed_files=[],
            enabled=False,
        )

        assert result is None
        assert validator.calls == []

    def test_validates_materialized_branch_when_enabled(self) -> None:
        validator = _FakeReviewBranchValidator(ValidationResult.safe())
        use_case = ValidateReviewBranchUseCase(validator)  # type: ignore[arg-type]
        profile = ProjectProfile("python", "python", None, "pytest", True)
        changed_files = [
            ChangedFile(
                path=Path("app/service.py"),
                change_type=ChangeType.MODIFIED,
                language=Language.PYTHON,
                diff_content="",
            )
        ]

        result = use_case.execute(
            review_branch=ReviewBranchMaterialization(branch_name="feature_refactor", commit_sha="abc123"),
            repo_path="/repo",
            profile=profile,
            changed_files=changed_files,
            enabled=True,
        )

        assert result is not None
        assert result.passed is True
        assert validator.calls == [
            ("feature_refactor", "/repo", "python", ["app/service.py"])
        ]