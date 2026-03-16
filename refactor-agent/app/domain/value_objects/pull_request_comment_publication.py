from dataclasses import dataclass


@dataclass(frozen=True)
class PullRequestCommentPublication:
    """Details of an idempotent PR summary comment published by the agent."""

    comment_id: int
    url: str
    updated: bool = False