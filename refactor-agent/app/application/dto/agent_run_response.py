from dataclasses import dataclass
from typing import Optional

from app.domain.value_objects.agent_run_result import AgentRunResult


@dataclass
class AgentRunResponse:
    """DTO carrying the outcome of a governance agent run back to the entrypoint."""

    success: bool
    result: Optional[AgentRunResult] = None
    error: Optional[str] = None
