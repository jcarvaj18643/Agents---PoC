from enum import Enum


class Severity(str, Enum):
    """Severity level for validation issues and refactor suggestions."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
