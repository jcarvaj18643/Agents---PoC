from enum import Enum


class ValidationStatus(str, Enum):
    """Eligibility state for advisory refactor suggestions."""

    SAFE = "safe"
    UNSAFE = "unsafe"
    REFUSED = "refused"
    SKIPPED = "skipped"