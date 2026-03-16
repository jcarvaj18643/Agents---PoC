from app.application.ports.outbound.pull_request_comment_publisher_port import (
    PullRequestCommentPublisherPort,
)
from app.domain.value_objects.agent_run_result import AgentRunResult
from app.domain.value_objects.pull_request_comment_publication import (
    PullRequestCommentPublication,
)


class PublishPullRequestCommentUseCase:
    """Publish or update a compact agent summary comment on a pull request."""

    def __init__(
        self,
        pull_request_comment_publisher: PullRequestCommentPublisherPort,
    ) -> None:
        self._pull_request_comment_publisher = pull_request_comment_publisher

    def execute(
        self,
        result: AgentRunResult,
        repository: str | None,
        pull_request_number: int | None,
        enabled: bool,
    ) -> PullRequestCommentPublication | None:
        if not enabled or not repository or pull_request_number is None:
            return None

        return self._pull_request_comment_publisher.publish(
            repository=repository,
            pull_request_number=pull_request_number,
            body=self._render_comment(result),
        )

    def _render_comment(self, result: AgentRunResult) -> str:
        validation_status = (
            result.validation_result.status.value if result.validation_result else "not-evaluated"
        )
        lines = [
            "<!-- engineering-governance-agent:summary -->",
            "## Engineering Governance Agent",
            "",
            f"- Run status: `{result.execution_status}`",
            f"- Governance status: `{result.governance_status}`",
            f"- Validation status: `{validation_status}`",
            f"- Changed files: `{len(result.changed_files)}`",
            f"- Refactor suggestions: `{len(result.refactor_suggestions)}`",
            f"- Patch previews: `{len(result.refactor_patches)}`",
        ]
        if result.review_branch is not None:
            lines.append(f"- Review branch: `{result.review_branch.branch_name}`")
        if result.review_branch_validation_result is not None:
            lines.append(
                f"- Review branch validation: `{result.review_branch_validation_result.status.value}`"
            )
        if result.review_pull_request is not None:
            lines.append(f"- Review PR: #{result.review_pull_request.number}")
        if result.report_path:
            lines.append(f"- Report artifact path: `{result.report_path}`")
        return "\n".join(lines)