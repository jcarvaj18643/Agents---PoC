from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReviewBranchMaterialization:
    """Details of a review branch created from approved refactor patches."""

    branch_name: str
    commit_sha: str
    pushed: bool = False
    remote_ref: str | None = None
    committed_files: tuple[str, ...] = field(default_factory=tuple)