from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class ExecutionContext:
    """Runtime context for a single agent invocation.

    Captures how, where, and by whom the agent was triggered.
    Downstream components can read this to adapt their behaviour
    (e.g. dry-run vs. apply mode, CI vs. local).
    """

    run_id: str
    triggered_by: str  # "github_actions" | "cli" | "api"
    repository_path: Path
    base_ref: str
    head_ref: str
    started_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    github_event: Optional[str] = None
    pull_request_number: Optional[int] = None
