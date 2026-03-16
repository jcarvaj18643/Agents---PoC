class DomainException(Exception):
    """Base class for all domain-layer exceptions."""


class EmptyScopeError(DomainException):
    """Raised when a required CodeScope contains no changed files."""


class InvalidProfileError(DomainException):
    """Raised when the project profile cannot be determined from the repository."""


class PolicyNotFoundError(DomainException):
    """Raised when no engineering policy matches the given project profile."""


class UnsafeRefactorError(DomainException):
    """Raised when an attempted refactor fails safety validation."""
