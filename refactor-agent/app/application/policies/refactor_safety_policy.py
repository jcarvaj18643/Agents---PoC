import re
from typing import List

from app.domain.entities.changed_file import ChangedFile
from app.domain.enums.change_type import ChangeType
from app.domain.entities.refactor_suggestion import RefactorSuggestion
from app.domain.enums.severity import Severity
from app.domain.value_objects.project_profile import ProjectProfile
from app.domain.value_objects.validation_result import ValidationIssue, ValidationResult

CSHARP_PUBLIC_API_RE = re.compile(r"\bpublic\s+(interface|record|enum)\b")
TYPESCRIPT_PUBLIC_API_RE = re.compile(r"\bexport\s+(interface|type|enum|function)\b")
PYTHON_PUBLIC_API_RE = re.compile(r"^(def|class)\s+([A-Za-z][A-Za-z0-9_]*)")
CSHARP_PUBLIC_API_PATH_HINTS = ("/abstractions/", "/contracts/", "/interfaces/")
TEST_PATH_HINTS = ("/test/", "/tests/", "/__tests__/", ".spec.", ".test.")


class RefactorSafetyPolicy:
    """Application-level policy that evaluates whether refactor suggestions are safe.

    This is intentionally kept in the application layer (not infrastructure) because
    it encodes business rules about what constitutes a safe change, independent of
    any external tool or framework.
    """

    def __init__(
        self,
        max_suggestions_per_run: int = 10,
        enforce_public_api_guard: bool = True,
    ) -> None:
        self._max_suggestions = max_suggestions_per_run
        self._enforce_public_api_guard = enforce_public_api_guard

    def evaluate(
        self,
        suggestions: List[RefactorSuggestion],
        changed_files: List[ChangedFile],
        profile: ProjectProfile,
    ) -> ValidationResult:
        """Return a ValidationResult indicating whether suggestions pass all safety gates."""
        issues: List[ValidationIssue] = []

        if len(suggestions) > self._max_suggestions:
            issues.append(
                ValidationIssue(
                    code="POLICY_001",
                    message=(
                        f"Too many suggestions ({len(suggestions)}); "
                        f"max allowed per run is {self._max_suggestions}."
                    ),
                    severity=Severity.WARNING,
                    file_path="",
                )
            )

        public_api_file = self._find_public_api_change(changed_files, profile)
        if self._enforce_public_api_guard and public_api_file is not None:
            issues.append(
                ValidationIssue(
                    code="POLICY_PUBLIC_API_REVIEW_REQUIRED",
                    message=(
                        f"Changed scope touches public API surface in {public_api_file.path.as_posix()}. "
                        "Require explicit review before any apply-capable mode is considered."
                    ),
                    severity=Severity.ERROR,
                    file_path=public_api_file.path.as_posix(),
                )
            )

        # Additional policy gates can extend this evaluation without changing callers.
        if issues:
            return ValidationResult.refused(issues)
        return ValidationResult.safe()

    def _find_public_api_change(
        self,
        changed_files: List[ChangedFile],
        profile: ProjectProfile,
    ) -> ChangedFile | None:
        for changed_file in changed_files:
            if self._path_or_diff_touches_public_api(changed_file, profile):
                return changed_file
        return None

    def _path_or_diff_touches_public_api(
        self,
        changed_file: ChangedFile,
        profile: ProjectProfile,
    ) -> bool:
        normalized_path = changed_file.path.as_posix().lower()
        if self._is_test_file(normalized_path):
            return False
        if profile.language == "csharp" and any(hint in normalized_path for hint in CSHARP_PUBLIC_API_PATH_HINTS):
            return True
        if profile.language == "typescript" and normalized_path.endswith("public-api.ts"):
            return True
        if profile.language == "python" and changed_file.path.name == "__init__.py":
            return True
        return self._diff_touches_public_api(changed_file, profile)

    def _diff_touches_public_api(
        self,
        changed_file: ChangedFile,
        profile: ProjectProfile,
    ) -> bool:
        changed_lines = [
            line[1:].strip()
            for line in changed_file.diff_content.splitlines()
            if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
        ]
        if profile.language == "csharp":
            return any(CSHARP_PUBLIC_API_RE.search(line) for line in changed_lines)
        if profile.language == "typescript":
            return any(
                TYPESCRIPT_PUBLIC_API_RE.search(line) or line.startswith("@Input(") or line.startswith("@Output(")
                for line in changed_lines
            )
        if profile.language == "python":
            return any(self._is_python_public_symbol(line) for line in changed_lines)
        return False

    def _is_python_public_symbol(self, line: str) -> bool:
        match = PYTHON_PUBLIC_API_RE.match(line)
        if not match:
            return False
        symbol_name = match.group(2)
        return not symbol_name.startswith("_")

    def _is_test_file(self, normalized_path: str) -> bool:
        file_name = normalized_path.rsplit("/", maxsplit=1)[-1]
        return any(hint in normalized_path for hint in TEST_PATH_HINTS) or file_name.startswith("test_")
