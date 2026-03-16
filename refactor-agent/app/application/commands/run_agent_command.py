from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RunAgentCommand:
    """Command object expressing the intent to run the governance agent.

    Immutable by design: commands represent a decision that has already been made.
    Maps 1-to-1 with AgentRunRequest but lives in the application layer as a
    first-class command concept, separate from the transport-level DTO.
    """

    repo_path: str
    base_ref: str
    head_ref: str
    run_id: str
    triggered_by: str = "cli"
    dry_run: bool = True
    pull_request_number: Optional[int] = None
