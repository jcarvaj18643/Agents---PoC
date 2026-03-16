from abc import ABC, abstractmethod

from app.domain.value_objects.pull_request_publication import PullRequestPublication


class PullRequestPublisherPort(ABC):
    """Outbound port for creating or reusing a review pull request."""

    @abstractmethod
    def publish(
        self,
        repository: str,
        base_branch: str,
        head_branch: str,
        title: str,
        body: str,
    ) -> PullRequestPublication:
        ...