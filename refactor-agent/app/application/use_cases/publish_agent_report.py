from app.application.ports.outbound.report_publisher_port import ReportPublisherPort
from app.domain.value_objects.agent_run_result import AgentRunResult


class PublishAgentReportUseCase:
    """Use case: publish the final agent run result as a distributable report artifact."""

    def __init__(self, report_publisher: ReportPublisherPort) -> None:
        self._report_publisher = report_publisher

    def execute(self, result: AgentRunResult) -> str:
        # TODO: enrich result with run metadata before publishing (duration, stats)
        return self._report_publisher.publish(result)
