from pathlib import Path

from app.domain.entities.changed_file import ChangedFile
from app.domain.enums.change_type import ChangeType
from app.domain.enums.language import Language
from app.domain.value_objects.project_profile import ProjectProfile
from app.domain.value_objects.review_branch_materialization import (
    ReviewBranchMaterialization,
)
from app.domain.value_objects.validation_result import ValidationResult
from app.infrastructure.adapters.git.review_branch_validator_adapter import (
    GitReviewBranchValidatorAdapter,
)


class _FakeValidationRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, list[str]]] = []

    def validate(self, repo_path, profile, changed_files):  # type: ignore[no-untyped-def]
        self.calls.append(
            (
                repo_path,
                profile.name,
                [changed_file.path.as_posix() for changed_file in changed_files],
            )
        )
        return ValidationResult.safe(executed_checks=["TEST:repo-wide -> pytest -q"])


class TestGitReviewBranchValidatorAdapter:
    def test_validates_branch_in_isolated_worktree(self, tmp_path: Path) -> None:
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        app_dir = repo_path / "app"
        app_dir.mkdir()
        (app_dir / "service.py").write_text("def run() -> int:\n    return 1\n", encoding="utf-8")

        import subprocess

        def git(*args: str) -> None:
            subprocess.run(["git", *args], cwd=repo_path, check=True, capture_output=True)

        git("init", "-b", "main")
        git("config", "user.email", "test@example.com")
        git("config", "user.name", "Test User")
        git("add", ".")
        git("commit", "-m", "initial")
        git("checkout", "-b", "feature_refactor")

        runner = _FakeValidationRunner()
        adapter = GitReviewBranchValidatorAdapter(runner)  # type: ignore[arg-type]
        profile = ProjectProfile("python", "python", None, "pytest", True)
        changed_files = [
            ChangedFile(
                path=Path("app/service.py"),
                change_type=ChangeType.MODIFIED,
                language=Language.PYTHON,
                diff_content="",
            )
        ]

        result = adapter.validate(
            review_branch=ReviewBranchMaterialization(branch_name="feature_refactor", commit_sha="abc123"),
            repo_path=str(repo_path),
            profile=profile,
            changed_files=changed_files,
        )

        assert result.passed is True
        assert len(runner.calls) == 1
        validated_repo_path, profile_name, validated_files = runner.calls[0]
        assert profile_name == "python"
        assert validated_files == ["app/service.py"]
        assert validated_repo_path != str(repo_path)
        assert Path(validated_repo_path).exists() is False