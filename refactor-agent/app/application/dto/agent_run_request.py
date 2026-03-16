from dataclasses import dataclass
from typing import Optional


@dataclass
class AgentRunRequest:
    """DTO carrying all inputs needed to start the governance agent.

    Constructed by entrypoints (CLI, GitHub Actions runner) and passed
    to the inbound port. Contains no business logic.
    """

    repo_path: str
    base_ref: str
    head_ref: str
    run_id: str
    triggered_by: str = "cli"
    dry_run: bool = True
    apply_refactors: bool = False
    publish_review_branch: bool = False
    push_review_branch: bool = False
    review_branch_name: Optional[str] = None
    review_remote_name: str = "origin"
    repository: Optional[str] = None
    base_branch: Optional[str] = None
    head_branch: Optional[str] = None
    publish_pr_comment: bool = False
    create_review_pull_request: bool = False
    pull_request_number: Optional[int] = None
