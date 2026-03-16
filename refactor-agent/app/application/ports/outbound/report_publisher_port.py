from abc import ABC, abstractmethod

from app.domain.value_objects.agent_run_result import AgentRunResult


class ReportPublisherPort(ABC):
    """Outbound port — serialises and publishes the final agent run result."""

    @abstractmethod
    def publish(self, result: AgentRunResult) -> str:
        """Publish the report and return the artifact path or URL."""
        ...
