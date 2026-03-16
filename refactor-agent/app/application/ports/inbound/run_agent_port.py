from abc import ABC, abstractmethod

from app.application.dto.agent_run_request import AgentRunRequest
from app.application.dto.agent_run_response import AgentRunResponse


class RunAgentPort(ABC):
    """Inbound port — the primary driver interface for the governance agent.

    Any entrypoint (CLI, GitHub Actions runner, HTTP handler) must call this
    contract to trigger a run, ensuring that entrypoints stay decoupled from
    the orchestration logic.
    """

    @abstractmethod
    def run(self, request: AgentRunRequest) -> AgentRunResponse:
        """Execute a full governance agent run and return the aggregated response."""
        ...
