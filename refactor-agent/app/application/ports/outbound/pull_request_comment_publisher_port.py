from abc import ABC, abstractmethod

from app.domain.value_objects.pull_request_comment_publication import (
    PullRequestCommentPublication,
)


class PullRequestCommentPublisherPort(ABC):
    """Outbound port for publishing an idempotent summary comment to a pull request."""

    @abstractmethod
    def publish(
        self,
        repository: str,
        pull_request_number: int,
        body: str,
    ) -> PullRequestCommentPublication:
        ...