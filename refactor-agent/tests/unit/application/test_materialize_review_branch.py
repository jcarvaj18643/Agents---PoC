from pathlib import Path

from app.application.use_cases.materialize_review_branch import (
    MaterializeReviewBranchUseCase,
)
from app.domain.entities.refactor_patch import RefactorPatch
from app.domain.enums.refactor_status import RefactorStatus
from app.domain.value_objects.review_branch_materialization import (
    ReviewBranchMaterialization,
)
from app.domain.value_objects.validation_result import ValidationResult


class _FakePublisher:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], str, str, str | None, bool, str]] = []

    def publish(
        self,
        patches,
        repo_path: str,
        start_ref: str,
        branch_name: str | None = None,
        push: bool = False,
        remote_name: str = "origin",
    ) -> ReviewBranchMaterialization:
        self.calls.append(
            ([patch.file_path.as_posix() for patch in patches], repo_path, start_ref, branch_name, push, remote_name)
        )
        return ReviewBranchMaterialization(
            branch_name=branch_name or "feature_refactor",
            commit_sha="abc123",
            pushed=push,
            remote_ref=f"{remote_name}/{branch_name or 'feature_refactor'}" if push else None,
            committed_files=tuple(patch.file_path.as_posix() for patch in patches),
        )


class TestMaterializeReviewBranchUseCase:
    def test_skips_when_feature_is_disabled(self) -> None:
        publisher = _FakePublisher()
        use_case = MaterializeReviewBranchUseCase(publisher)

        result = use_case.execute(
            [],
            "/repo",
            "feature/main",
            ValidationResult.safe(),
            enabled=False,
        )

        assert result is None
        assert publisher.calls == []

    def test_skips_when_validation_failed(self) -> None:
        publisher = _FakePublisher()
        use_case = MaterializeReviewBranchUseCase(publisher)

        result = use_case.execute(
            [
                RefactorPatch(
                    suggestion_id="1",
                    file_path=Path("app.py"),
                    original_chunk="return 1",
                    patched_chunk="return 2",
                    status=RefactorStatus.VALIDATED,
                )
            ],
            "/repo",
            "feature/main",
            ValidationResult.unsafe(summary="blocked"),
            enabled=True,
        )

        assert result is None
        assert publisher.calls == []

    def test_publishes_only_approved_patches(self) -> None:
        publisher = _FakePublisher()
        use_case = MaterializeReviewBranchUseCase(publisher)

        result = use_case.execute(
            [
                RefactorPatch(
                    suggestion_id="1",
                    file_path=Path("app.py"),
                    original_chunk="return 1",
                    patched_chunk="return 2",
                    status=RefactorStatus.VALIDATED,
                ),
                RefactorPatch(
                    suggestion_id="2",
                    file_path=Path("ignored.py"),
                    original_chunk="return 1",
                    patched_chunk="return 2",
                    status=RefactorStatus.REJECTED,
                ),
            ],
            "/repo",
            "feature/main",
            ValidationResult.safe(),
            enabled=True,
            branch_name="ticket123_refactor",
            push=True,
            remote_name="upstream",
        )

        assert result is not None
        assert result.branch_name == "ticket123_refactor"
        assert publisher.calls == [
            (["app.py"], "/repo", "feature/main", "ticket123_refactor", True, "upstream")
        ]