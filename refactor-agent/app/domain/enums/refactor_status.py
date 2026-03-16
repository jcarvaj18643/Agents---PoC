from enum import Enum


class RefactorStatus(str, Enum):
    """Lifecycle state of a refactor patch."""

    PENDING = "pending"
    VALIDATED = "validated"
    APPLIED = "applied"
    REJECTED = "rejected"
    FAILED = "failed"
