from dataclasses import dataclass


@dataclass(frozen=True)
class PullRequestPublication:
    """Details of a review pull request created or reused by the agent."""

    number: int
    url: str
    head_branch: str
    base_branch: str
    created: bool = False