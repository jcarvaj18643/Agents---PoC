from datetime import datetime, timezone

from app.application.use_cases.publish_pull_request_comment import (
    PublishPullRequestCommentUseCase,
)
from app.domain.value_objects.agent_run_result import AgentRunResult
from app.domain.value_objects.pull_request_comment_publication import (
    PullRequestCommentPublication,
)
from app.domain.value_objects.review_branch_materialization import (
    ReviewBranchMaterialization,
)


class _FakeCommentPublisher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, str]] = []

    def publish(self, repository: str, pull_request_number: int, body: str) -> PullRequestCommentPublication:
        self.calls.append((repository, pull_request_number, body))
        return PullRequestCommentPublication(
            comment_id=1234,
            url="https://github.com/acme/refactor-agent/pull/99#issuecomment-1234",
            updated=False,
        )


class TestPublishPullRequestCommentUseCase:
    def test_skips_when_disabled(self) -> None:
        publisher = _FakeCommentPublisher()
        use_case = PublishPullRequestCommentUseCase(publisher)

        result = use_case.execute(
            AgentRunResult(
                run_id="run-1",
                success=True,
                completed_at=datetime.now(timezone.utc),
            ),
            "acme/refactor-agent",
            99,
            enabled=False,
        )

        assert result is None
        assert publisher.calls == []

    def test_publishes_summary_comment(self) -> None:
        publisher = _FakeCommentPublisher()
        use_case = PublishPullRequestCommentUseCase(publisher)

        result = use_case.execute(
            AgentRunResult(
                run_id="run-1",
                success=True,
                completed_at=datetime.now(timezone.utc),
                review_branch=ReviewBranchMaterialization(
                    branch_name="ticket123_refactor",
                    commit_sha="abc123",
                ),
            ),
            "acme/refactor-agent",
            99,
            enabled=True,
        )

        assert result is not None
        assert result.comment_id == 1234
        assert publisher.calls[0][0:2] == ("acme/refactor-agent", 99)
        assert "engineering-governance-agent:summary" in publisher.calls[0][2]