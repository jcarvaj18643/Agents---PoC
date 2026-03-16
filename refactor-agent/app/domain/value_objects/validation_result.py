from dataclasses import dataclass, field
from typing import List

from app.domain.enums.severity import Severity
from app.domain.enums.validation_status import ValidationStatus


@dataclass(frozen=True)
class ValidationIssue:
    """A single problem found during a validation run."""

    code: str
    message: str
    severity: Severity
    file_path: str
    line: int = 0


@dataclass
class ValidationResult:
    """Aggregated result from a safety or quality validation run.

    The status makes validation eligibility explicit:
    - safe: eligible after policy and validator checks
    - unsafe: blocked by tool-based validation failures
    - refused: rejected by policy-level safety rules
    - skipped: validation was intentionally deferred to CI/CD
    """

    status: ValidationStatus
    issues: List[ValidationIssue] = field(default_factory=list)
    executed_checks: List[str] = field(default_factory=list)
    planned_checks: List[str] = field(default_factory=list)
    summary: str = ""

    @property
    def passed(self) -> bool:
        return self.status == ValidationStatus.SAFE

    @property
    def deferred(self) -> bool:
        return self.status == ValidationStatus.SKIPPED

    @property
    def critical_issues(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.CRITICAL]

    @property
    def error_issues(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @classmethod
    def safe(
        cls,
        issues: List[ValidationIssue] | None = None,
        executed_checks: List[str] | None = None,
        planned_checks: List[str] | None = None,
        summary: str = "",
    ) -> "ValidationResult":
        return cls(
            status=ValidationStatus.SAFE,
            issues=issues or [],
            executed_checks=executed_checks or [],
            planned_checks=planned_checks or [],
            summary=summary,
        )

    @classmethod
    def unsafe(
        cls,
        issues: List[ValidationIssue] | None = None,
        executed_checks: List[str] | None = None,
        planned_checks: List[str] | None = None,
        summary: str = "",
    ) -> "ValidationResult":
        return cls(
            status=ValidationStatus.UNSAFE,
            issues=issues or [],
            executed_checks=executed_checks or [],
            planned_checks=planned_checks or [],
            summary=summary,
        )

    @classmethod
    def refused(
        cls,
        issues: List[ValidationIssue] | None = None,
        executed_checks: List[str] | None = None,
        planned_checks: List[str] | None = None,
        summary: str = "",
    ) -> "ValidationResult":
        return cls(
            status=ValidationStatus.REFUSED,
            issues=issues or [],
            executed_checks=executed_checks or [],
            planned_checks=planned_checks or [],
            summary=summary,
        )

    @classmethod
    def skipped(
        cls,
        issues: List[ValidationIssue] | None = None,
        planned_checks: List[str] | None = None,
        summary: str = "",
    ) -> "ValidationResult":
        return cls(
            status=ValidationStatus.SKIPPED,
            issues=issues or [],
            planned_checks=planned_checks or [],
            summary=summary,
        )
