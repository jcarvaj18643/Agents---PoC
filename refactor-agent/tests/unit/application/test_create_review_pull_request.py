from app.application.use_cases.create_review_pull_request import (
    CreateReviewPullRequestUseCase,
)
from app.domain.value_objects.pull_request_publication import PullRequestPublication
from app.domain.value_objects.review_branch_materialization import (
    ReviewBranchMaterialization,
)


class _FakePullRequestPublisher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str, str, str]] = []

    def publish(self, repository: str, base_branch: str, head_branch: str, title: str, body: str) -> PullRequestPublication:
        self.calls.append((repository, base_branch, head_branch, title, body))
        return PullRequestPublication(
            number=99,
            url="https://github.com/acme/refactor-agent/pull/99",
            head_branch=head_branch,
            base_branch=base_branch,
            created=True,
        )


class TestCreateReviewPullRequestUseCase:
    def test_skips_when_disabled(self) -> None:
        publisher = _FakePullRequestPublisher()
        use_case = CreateReviewPullRequestUseCase(publisher)

        result = use_case.execute(None, "acme/refactor-agent", "main", enabled=False)

        assert result is None
        assert publisher.calls == []

    def test_publishes_review_pull_request(self) -> None:
        publisher = _FakePullRequestPublisher()
        use_case = CreateReviewPullRequestUseCase(publisher)

        result = use_case.execute(
            ReviewBranchMaterialization(
                branch_name="ticket123_refactor",
                commit_sha="abc123",
                pushed=True,
                remote_ref="origin/ticket123_refactor",
            ),
            "acme/refactor-agent",
            "main",
            enabled=True,
        )

        assert result is not None
        assert result.number == 99
        assert publisher.calls[0][0:3] == (
            "acme/refactor-agent",
            "main",
            "ticket123_refactor",
        )