import re
from fnmatch import fnmatch
from typing import List

from app.application.ports.outbound.llm_refactor_advisor_port import LlmRefactorAdvisorPort
from app.domain.entities.changed_file import ChangedFile
from app.domain.entities.refactor_suggestion import RefactorSuggestion
from app.domain.enums.severity import Severity
from app.domain.value_objects.engineering_policy import EngineeringPolicy
from app.infrastructure.logging.console_logger import get_logger

logger = get_logger(__name__)

_PLACEHOLDER_ANCHOR_RE = re.compile(r"^(change-\d+|line\s+\d+|hunk|symbol|n/?a)$", re.IGNORECASE)
_LOW_SIGNAL_TEST_TITLES = {
    "Break up high-churn change",
    "Extract focused Python helpers",
    "Reduce Angular component/service branching",
    "Consolidate template or style repetition",
    "Review public API surface in changed class",
    "Isolate persistence responsibilities",
}


class GenerateRefactorSuggestionsUseCase:
    """Use case: generate refactor suggestions for changed files using an LLM.

    Keeps orchestration concerns in the application layer:
    select only refactor-relevant policies, scope them per file, then deduplicate
    and rank suggestions returned by the advisory adapter.
    """

    def __init__(self, llm_refactor_advisor: LlmRefactorAdvisorPort) -> None:
        self._llm_refactor_advisor = llm_refactor_advisor
        self.last_execution_mode = "not-invoked"

    def execute(
        self,
        files: List[ChangedFile],
        policies: List[EngineeringPolicy],
    ) -> List[RefactorSuggestion]:
        refactor_policies = self._select_refactor_policies(policies)
        if not refactor_policies:
            self.last_execution_mode = "not-invoked"
            return []

        logger.info(
            "Generating refactor suggestions for %d scoped file(s) across %d refactor policie(s)",
            len(files),
            len(refactor_policies),
        )

        suggestions: list[RefactorSuggestion] = []
        execution_modes: list[str] = []
        for changed_file in files:
            applicable_policies = self._select_applicable_policies(changed_file, refactor_policies)
            if not applicable_policies:
                continue
            suggestions.extend(self._llm_refactor_advisor.advise([changed_file], applicable_policies))
            execution_modes.append(getattr(self._llm_refactor_advisor, "last_execution_mode", "unknown"))

        self.last_execution_mode = self._summarize_execution_modes(execution_modes)

        return self._filter_low_signal_suggestions(self._rank_and_deduplicate(suggestions), files)

    def _select_refactor_policies(
        self,
        policies: List[EngineeringPolicy],
    ) -> list[EngineeringPolicy]:
        return [
            policy
            for policy in policies
            if any(rule.get("type") == "refactor" for rule in policy.rules)
        ]

    def _select_applicable_policies(
        self,
        changed_file: ChangedFile,
        policies: List[EngineeringPolicy],
    ) -> list[EngineeringPolicy]:
        path = changed_file.path.as_posix()
        file_name = changed_file.path.name
        return [
            policy
            for policy in policies
            if any(fnmatch(path, pattern) or fnmatch(file_name, pattern) for pattern in policy.applies_to)
        ]

    def _rank_and_deduplicate(
        self,
        suggestions: List[RefactorSuggestion],
    ) -> List[RefactorSuggestion]:
        ranked = sorted(
            suggestions,
            key=lambda suggestion: (
                self._severity_rank(suggestion.severity),
                suggestion.file_path,
                suggestion.title,
            ),
        )

        deduplicated: list[RefactorSuggestion] = []
        seen: set[tuple[str, str, str | None]] = set()
        for suggestion in ranked:
            key = (suggestion.file_path, suggestion.title, suggestion.rule_reference)
            if key in seen:
                continue
            seen.add(key)
            deduplicated.append(suggestion)

        return deduplicated

    def _severity_rank(self, severity: Severity) -> int:
        ranks = {
            Severity.CRITICAL: 0,
            Severity.ERROR: 1,
            Severity.WARNING: 2,
            Severity.INFO: 3,
        }
        return ranks[severity]

    def _summarize_execution_modes(self, execution_modes: list[str]) -> str:
        normalized_modes = [mode for mode in execution_modes if mode and mode != "unknown"]
        if not normalized_modes:
            return "not-invoked"
        unique_modes = set(normalized_modes)
        if len(unique_modes) == 1:
            return normalized_modes[0]
        return "mixed"

    def _filter_low_signal_suggestions(
        self,
        suggestions: List[RefactorSuggestion],
        files: List[ChangedFile],
    ) -> List[RefactorSuggestion]:
        file_lookup = {changed_file.path.as_posix(): changed_file for changed_file in files}
        filtered: list[RefactorSuggestion] = []
        for suggestion in suggestions:
            changed_file = file_lookup.get(suggestion.file_path)
            if not self._has_traceable_anchor(suggestion):
                continue
            if changed_file is not None and self._is_low_signal_test_suggestion(changed_file, suggestion):
                continue
            filtered.append(suggestion)
        return filtered

    def _has_traceable_anchor(self, suggestion: RefactorSuggestion) -> bool:
        if suggestion.impacted_symbol:
            return True
        if not suggestion.change_anchor:
            return False
        return _PLACEHOLDER_ANCHOR_RE.match(suggestion.change_anchor.strip()) is None

    def _is_low_signal_test_suggestion(
        self,
        changed_file: ChangedFile,
        suggestion: RefactorSuggestion,
    ) -> bool:
        normalized_path = changed_file.path.as_posix().lower()
        is_test_file = any(token in normalized_path for token in ("/test", "/tests", ".spec.", ".test.")) or changed_file.path.name.startswith("test_")
        return is_test_file and suggestion.severity == Severity.INFO and suggestion.title in _LOW_SIGNAL_TEST_TITLES
