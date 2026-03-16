from app.application.ports.outbound.pull_request_publisher_port import (
    PullRequestPublisherPort,
)
from app.domain.value_objects.pull_request_publication import PullRequestPublication
from app.domain.value_objects.review_branch_materialization import (
    ReviewBranchMaterialization,
)


class CreateReviewPullRequestUseCase:
    """Create or reuse a pull request for the materialized review branch."""

    def __init__(self, pull_request_publisher: PullRequestPublisherPort) -> None:
        self._pull_request_publisher = pull_request_publisher

    def execute(
        self,
        review_branch: ReviewBranchMaterialization | None,
        repository: str | None,
        base_branch: str | None,
        enabled: bool,
    ) -> PullRequestPublication | None:
        if not enabled or review_branch is None or not repository or not base_branch:
            return None

        return self._pull_request_publisher.publish(
            repository=repository,
            base_branch=base_branch,
            head_branch=review_branch.branch_name,
            title=f"Engineering Governance review: {review_branch.branch_name}",
            body=(
                "This pull request was materialized by the Engineering Governance Agent from approved refactor patches.\n\n"
                f"- Review branch: `{review_branch.branch_name}`\n"
                f"- Commit: `{review_branch.commit_sha}`\n"
                f"- Pushed: `{review_branch.pushed}`"
            ),
        )