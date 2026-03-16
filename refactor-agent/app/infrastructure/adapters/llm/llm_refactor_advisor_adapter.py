import re
import uuid
from typing import Any, List

from openai import OpenAI

from app.application.ports.outbound.llm_refactor_advisor_port import LlmRefactorAdvisorPort
from app.domain.entities.changed_file import ChangedFile
from app.domain.entities.refactor_suggestion import RefactorSuggestion
from app.domain.enums.language import Language
from app.domain.enums.severity import Severity
from app.domain.value_objects.engineering_policy import EngineeringPolicy
from app.infrastructure.adapters.llm.openai_response_utils import (
    extract_output_text,
    parse_json_object,
)
from app.infrastructure.logging.console_logger import get_logger

logger = get_logger(__name__)

_EVIDENCE_SCOPE_CHANGED_HUNK = "changed-hunk"
_EVIDENCE_SCOPE_CHANGED_AND_FILE = "changed-hunk+full-file"
_EVIDENCE_SCOPE_CHANGED_AND_SYMBOL = "changed-hunk+symbol"
_EVIDENCE_SCOPE_CHANGED_SYMBOL_AND_FILE = "changed-hunk+symbol+full-file"
_EMPTY_CONTEXT = "<empty>"
_LLM_MODE_REAL = "LLM real"
_LLM_MODE_FALLBACK = "fallback local"
_CALL_SYMBOL_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
_SYMBOL_STOP_WORDS = {"if", "for", "while", "switch", "return", "catch", "new"}
_WEAK_ANCHOR_RE = re.compile(r"^(change-\d+|line\s+\d+|hunk|symbol|n/?a)$", re.IGNORECASE)


class LlmRefactorAdvisorAdapter(LlmRefactorAdvisorPort):
    """Adapter: calls an LLM API to propose refactoring improvements.

    Uses a real OpenAI-compatible client when credentials are available and
    falls back to deterministic heuristics when they are not.
    """

    def __init__(self, model: str, api_key: str, client: Any | None = None) -> None:
        self._model = model
        self._api_key = api_key
        self._client = client or (OpenAI(api_key=api_key) if api_key else None)
        self.last_execution_mode = "not-invoked"

    def advise(
        self,
        files: List[ChangedFile],
        policies: List[EngineeringPolicy],
    ) -> List[RefactorSuggestion]:
        if not files or not policies:
            self.last_execution_mode = "not-invoked"
            return []

        if self._client is None:
            self.last_execution_mode = _LLM_MODE_FALLBACK
            logger.info(
                "Refactor advisor mode: %s [reason=no_api_key, files=%d, model=%s]",
                _LLM_MODE_FALLBACK,
                len(files),
                self._model,
            )
            return self._build_fallback_suggestions(files, policies)

        logger.info(
            "Refactor advisor mode: %s [files=%d, model=%s]",
            _LLM_MODE_REAL,
            len(files),
            self._model,
        )
        suggestions: list[RefactorSuggestion] = []
        execution_modes: list[str] = []
        for changed_file in files:
            for policy in policies:
                file_suggestions, execution_mode = self._build_llm_or_fallback_suggestions(changed_file, policy)
                suggestions.extend(file_suggestions)
                execution_modes.append(execution_mode)
        self.last_execution_mode = self._summarize_execution_modes(execution_modes)
        return suggestions

    def _build_fallback_suggestions(
        self,
        files: List[ChangedFile],
        policies: List[EngineeringPolicy],
    ) -> list[RefactorSuggestion]:
        suggestions: list[RefactorSuggestion] = []
        for changed_file in files:
            for policy in policies:
                suggestions.extend(self._build_file_suggestions(changed_file, policy))
        return suggestions

    def _build_llm_or_fallback_suggestions(
        self,
        changed_file: ChangedFile,
        policy: EngineeringPolicy,
    ) -> tuple[list[RefactorSuggestion], str]:
        try:
            response = self._client.responses.create(
                model=self._model,
                input=self._build_prompt(changed_file, policy),
            )
            parsed = parse_json_object(extract_output_text(response))
            llm_suggestions = self._parse_llm_suggestions(changed_file, policy, parsed)
            if llm_suggestions:
                logger.info(
                    "Refactor suggestions generated with %s [file=%s, policy=%s, suggestions=%d]",
                    _LLM_MODE_REAL,
                    changed_file.path,
                    policy.id,
                    len(llm_suggestions),
                )
                return llm_suggestions, _LLM_MODE_REAL
            logger.warning(
                "Refactor advisor received no usable structured suggestions and switched to %s [file=%s, policy=%s]",
                _LLM_MODE_FALLBACK,
                changed_file.path,
                policy.id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Refactor advisor switched to %s for %s after OpenAI error: %s",
                _LLM_MODE_FALLBACK,
                changed_file.path,
                exc,
            )
        return self._build_file_suggestions(changed_file, policy), _LLM_MODE_FALLBACK

    def _build_prompt(self, changed_file: ChangedFile, policy: EngineeringPolicy) -> str:
        symbol_name = changed_file.impacted_symbol.name if changed_file.impacted_symbol else "n/a"
        return "\n".join(
            [
                "You are a senior engineering reviewer generating refactor suggestions for changed code.",
                "Return exactly one JSON object with this shape:",
                '{"suggestions":[{"title":"...","description":"...","rationale":"...","severity":"info|warning|error","change_anchor":"...","suggested_code":"..."}]}',
                "Only suggest refactors justified by the changed code and nearby structural context.",
                "Do not suggest broad rewrites or changes outside the changed file.",
                "Only include suggested_code when you can express a concrete local replacement for the anchor in the same file.",
                "Repository guidance:",
                changed_file.repository_guidance or "No repository-specific guidance provided.",
                f"Policy id: {policy.id}",
                f"Policy name: {policy.name}",
                f"Policy description: {policy.description}",
                f"File: {changed_file.path.as_posix()}",
                f"Impacted symbol: {symbol_name}",
                "Changed hunk context:",
                changed_file.changed_hunk_context or _EMPTY_CONTEXT,
                "Symbol context:",
                changed_file.symbol_context or _EMPTY_CONTEXT,
                "Full file context:",
                changed_file.full_file_context or _EMPTY_CONTEXT,
            ]
        )

    def _parse_llm_suggestions(
        self,
        changed_file: ChangedFile,
        policy: EngineeringPolicy,
        parsed: dict[str, Any],
    ) -> list[RefactorSuggestion]:
        raw_suggestions = parsed.get("suggestions")
        if not isinstance(raw_suggestions, list):
            return []

        suggestions: list[RefactorSuggestion] = []
        for raw_item in raw_suggestions:
            if not isinstance(raw_item, dict):
                continue
            title = raw_item.get("title")
            description = raw_item.get("description")
            rationale = raw_item.get("rationale")
            if not all(isinstance(value, str) and value.strip() for value in (title, description, rationale)):
                continue
            suggestions.append(
                self._make_suggestion(
                    changed_file=changed_file,
                    policy=policy,
                    title=title.strip(),
                    description=description.strip(),
                    rationale=rationale.strip(),
                    severity=self._parse_severity(raw_item.get("severity")),
                    evidence_scope=self._resolve_evidence_scope(changed_file),
                    change_anchor=self._normalize_change_anchor(raw_item.get("change_anchor"), changed_file),
                    suggested_code=self._normalize_suggested_code(raw_item.get("suggested_code")),
                )
            )
        return suggestions

    def _parse_severity(self, raw_severity: Any) -> Severity:
        if not isinstance(raw_severity, str):
            return Severity.INFO
        normalized = raw_severity.strip().lower()
        mapping = {
            "critical": Severity.CRITICAL,
            "error": Severity.ERROR,
            "warning": Severity.WARNING,
            "warn": Severity.WARNING,
            "info": Severity.INFO,
        }
        return mapping.get(normalized, Severity.INFO)

    def _normalize_change_anchor(self, raw_anchor: Any, changed_file: ChangedFile) -> str | None:
        if isinstance(raw_anchor, str) and raw_anchor.strip():
            normalized_anchor = raw_anchor.strip()[:140]
            if _WEAK_ANCHOR_RE.match(normalized_anchor) is None:
                return normalized_anchor
        return self._extract_change_anchor(changed_file.changed_hunk_context) or (
            changed_file.impacted_symbol.name if changed_file.impacted_symbol else None
        )

    def _normalize_suggested_code(self, raw_code: Any) -> str | None:
        if not isinstance(raw_code, str):
            return None
        normalized = raw_code.strip()
        return normalized or None

    def _build_file_suggestions(
        self,
        changed_file: ChangedFile,
        policy: EngineeringPolicy,
    ) -> list[RefactorSuggestion]:
        suggestions: list[RefactorSuggestion] = []
        churn = changed_file.added_lines + changed_file.removed_lines
        path = changed_file.path.as_posix()
        change_context = changed_file.changed_hunk_context
        symbol_context = changed_file.symbol_context or changed_file.full_file_context or change_context
        full_context = changed_file.full_file_context or symbol_context
        evidence_scope = self._resolve_evidence_scope(changed_file)
        is_test_file = self._is_test_file(changed_file.path.as_posix())

        if churn >= 40 and not is_test_file:
            suggestions.append(
                self._make_suggestion(
                    changed_file=changed_file,
                    policy=policy,
                    title="Break up high-churn change",
                    description="This change touches many lines in one file. Consider extracting smaller methods or collaborators before the next iteration.",
                    rationale=f"The scoped diff changed {churn} lines in {path}, which raises review and regression risk.",
                    severity=Severity.WARNING,
                    evidence_scope=evidence_scope,
                    change_anchor=self._extract_change_anchor(change_context),
                )
            )

        if "TODO" in change_context or "NotImplemented" in change_context:
            suggestions.append(
                self._make_suggestion(
                    changed_file=changed_file,
                    policy=policy,
                    title="Resolve temporary implementation markers",
                    description="Replace TODO or NotImplemented markers with explicit follow-up tasks or completed local refactors.",
                    rationale="Temporary markers in changed code often indicate unfinished branching logic or deferred error handling.",
                    severity=Severity.WARNING,
                    evidence_scope=evidence_scope,
                    change_anchor=self._extract_change_anchor(change_context),
                )
            )

        duplicate_logic_suggestion = self._build_repetition_suggestion(
            changed_file,
            policy,
            change_context,
            symbol_context,
            full_context,
        )
        if duplicate_logic_suggestion is not None:
            suggestions.append(duplicate_logic_suggestion)

        suggestions.extend(
            self._build_language_specific_suggestions(
                changed_file,
                policy,
                churn,
                change_context,
                symbol_context,
                full_context,
            )
        )
        return suggestions

    def _build_language_specific_suggestions(
        self,
        changed_file: ChangedFile,
        policy: EngineeringPolicy,
        churn: int,
        change_context: str,
        symbol_context: str,
        full_context: str,
    ) -> list[RefactorSuggestion]:
        language = changed_file.language
        path = changed_file.path.as_posix().lower()
        is_test_file = self._is_test_file(changed_file.path.as_posix())

        if language == Language.PYTHON and churn >= 25:
            if is_test_file:
                return []
            return [self._build_python_suggestion(changed_file, policy)]

        if language == Language.CSHARP:
            return self._build_csharp_suggestions(
                changed_file,
                policy,
                churn,
                change_context,
                symbol_context,
                full_context,
                path,
            )

        if language == Language.TYPESCRIPT and ("component" in path or "service" in path):
            if is_test_file:
                return []
            return [self._build_typescript_suggestion(changed_file, policy, churn)]

        if language in {Language.HTML, Language.SCSS} and churn >= 20:
            if is_test_file:
                return []
            return [self._build_markup_style_suggestion(changed_file, policy)]

        return []

    def _build_python_suggestion(
        self,
        changed_file: ChangedFile,
        policy: EngineeringPolicy,
    ) -> RefactorSuggestion:
        return self._make_suggestion(
            changed_file=changed_file,
            policy=policy,
            title="Extract focused Python helpers",
            description="Split dense Python logic into smaller private helpers or fixtures to keep responsibilities narrow.",
            rationale="Python files with concentrated diff churn become harder to test and reason about when orchestration and transformation stay mixed.",
            severity=Severity.INFO,
            evidence_scope=self._resolve_evidence_scope(changed_file),
            change_anchor=self._extract_change_anchor(changed_file.changed_hunk_context),
        )

    def _build_csharp_suggestions(
        self,
        changed_file: ChangedFile,
        policy: EngineeringPolicy,
        churn: int,
        change_context: str,
        symbol_context: str,
        full_context: str,
        path: str,
    ) -> list[RefactorSuggestion]:
        if "repository" in path or "reader" in path or "writer" in path:
            return [
                self._make_suggestion(
                    changed_file=changed_file,
                    policy=policy,
                    title="Isolate persistence responsibilities",
                    description="Separate query composition, mapping, and persistence orchestration into narrower methods or collaborators.",
                    rationale="Repository and reader/writer classes accumulate data access concerns quickly, especially when a single diff touches both mapping and transaction logic.",
                    severity=Severity.INFO if churn < 50 else Severity.WARNING,
                    evidence_scope=self._resolve_evidence_scope(changed_file),
                    change_anchor=self._extract_change_anchor(change_context),
                )
            ]
        if symbol_context.count("public ") >= 3 and churn >= 20:
            return [
                self._make_suggestion(
                    changed_file=changed_file,
                    policy=policy,
                    title="Review public API surface in changed class",
                    description="Consider moving new behaviors behind smaller interfaces or internal methods to reduce public surface growth.",
                    rationale="Multiple public members in a changed C# class can signal growing responsibilities and tighter coupling.",
                    severity=Severity.INFO,
                    evidence_scope=self._resolve_evidence_scope(changed_file),
                    change_anchor=self._extract_change_anchor(change_context),
                )
            ]
        return []

    def _build_typescript_suggestion(
        self,
        changed_file: ChangedFile,
        policy: EngineeringPolicy,
        churn: int,
    ) -> RefactorSuggestion:
        return self._make_suggestion(
            changed_file=changed_file,
            policy=policy,
            title="Reduce Angular component/service branching",
            description="Move formatting, mapping, or branching-heavy logic into focused helpers so the Angular surface stays thin.",
            rationale="Angular components and services are easier to test when UI orchestration stays separate from data shaping and branching logic.",
            severity=Severity.INFO if churn < 40 else Severity.WARNING,
            evidence_scope=self._resolve_evidence_scope(changed_file),
            change_anchor=self._extract_change_anchor(changed_file.changed_hunk_context),
        )

    def _build_markup_style_suggestion(
        self,
        changed_file: ChangedFile,
        policy: EngineeringPolicy,
    ) -> RefactorSuggestion:
        return self._make_suggestion(
            changed_file=changed_file,
            policy=policy,
            title="Consolidate template or style repetition",
            description="Look for repeated blocks or selectors introduced by the change and extract shared structure where practical.",
            rationale="Large template/style diffs often indicate duplication that can be reduced before it spreads to sibling components.",
            severity=Severity.INFO,
            evidence_scope=self._resolve_evidence_scope(changed_file),
            change_anchor=self._extract_change_anchor(changed_file.changed_hunk_context),
        )

    def _summarize_execution_modes(self, execution_modes: list[str]) -> str:
        if not execution_modes:
            return "not-invoked"
        unique_modes = set(execution_modes)
        if len(unique_modes) == 1:
            return execution_modes[0]
        return "mixed"

    def _build_repetition_suggestion(
        self,
        changed_file: ChangedFile,
        policy: EngineeringPolicy,
        change_context: str,
        symbol_context: str,
        full_context: str,
    ) -> RefactorSuggestion | None:
        repeated_block = self._find_repeated_changed_block(change_context, symbol_context)
        repeated_symbol = self._find_repeated_symbol_usage(change_context, symbol_context)
        if not repeated_block:
            repeated_block = self._find_repeated_changed_block(change_context, full_context)
        if not repeated_symbol:
            repeated_symbol = self._find_repeated_symbol_usage(change_context, full_context)
        if not repeated_block and not repeated_symbol:
            return None

        rationale = "The recommendation is triggered by the new change"
        if repeated_block and repeated_symbol:
            rationale += ", and supported by a repeated block and repeated symbol elsewhere in the same changed file."
        elif repeated_block:
            rationale += ", and supported by a repeated block elsewhere in the same changed file."
        else:
            rationale += ", and supported by repeated symbol usage elsewhere in the same changed file."

        return self._make_suggestion(
            changed_file=changed_file,
            policy=policy,
            title="Extract or reuse repeated logic in changed file",
            description="The changed region matches a repeated block or repeatedly used symbol in the same file. Consider reusing an existing helper or extracting one local abstraction.",
            rationale=rationale,
            severity=Severity.INFO,
            evidence_scope=self._resolve_evidence_scope(changed_file),
            change_anchor=self._anchor_from_block(repeated_block) or repeated_symbol,
        )

    def _resolve_evidence_scope(self, changed_file: ChangedFile) -> str:
        if changed_file.impacted_symbol and changed_file.full_file_context:
            return _EVIDENCE_SCOPE_CHANGED_SYMBOL_AND_FILE
        if changed_file.impacted_symbol:
            return _EVIDENCE_SCOPE_CHANGED_AND_SYMBOL
        if changed_file.full_file_context:
            return _EVIDENCE_SCOPE_CHANGED_AND_FILE
        return _EVIDENCE_SCOPE_CHANGED_HUNK

    def _find_repeated_changed_block(self, change_context: str, full_context: str) -> str | None:
        meaningful_lines = [
            line.strip()
            for line in change_context.splitlines()
            if self._is_meaningful_repetition_candidate(line.strip())
        ]
        if len(meaningful_lines) < 2:
            return None

        normalized_full = "\n".join(line.strip() for line in full_context.splitlines())
        max_window = min(4, len(meaningful_lines))
        for window_size in range(max_window, 1, -1):
            for index in range(0, len(meaningful_lines) - window_size + 1):
                block = "\n".join(meaningful_lines[index : index + window_size])
                if normalized_full.count(block) >= 2:
                    return block
        return None

    def _find_repeated_symbol_usage(self, change_context: str, full_context: str) -> str | None:
        candidates: list[str] = []
        for symbol in _CALL_SYMBOL_RE.findall(change_context):
            if symbol.lower() in _SYMBOL_STOP_WORDS:
                continue
            if symbol not in candidates:
                candidates.append(symbol)

        for symbol in candidates:
            if full_context.count(f"{symbol}(") >= 2:
                return symbol
        return None

    def _anchor_from_block(self, block: str | None) -> str | None:
        if not block:
            return None
        return block.splitlines()[0][:140]

    def _is_meaningful_repetition_candidate(self, line: str) -> bool:
        if len(line) < 12:
            return False
        if line.startswith("@@"):
            return False
        if line in {"{", "}", "(", ")"}:
            return False
        return any(character.isalpha() for character in line)

    def _extract_change_anchor(self, change_context: str) -> str | None:
        for line in change_context.splitlines():
            candidate = line.strip()
            if self._is_meaningful_repetition_candidate(candidate):
                return candidate[:140]
        return None

    def _is_test_file(self, file_path: str) -> bool:
        normalized_path = file_path.lower()
        file_name = normalized_path.rsplit("/", maxsplit=1)[-1]
        return any(token in normalized_path for token in ("/test", "/tests", ".spec.", ".test.")) or file_name.startswith("test_")

    def _make_suggestion(
        self,
        changed_file: ChangedFile,
        policy: EngineeringPolicy,
        title: str,
        description: str,
        rationale: str,
        severity: Severity,
        evidence_scope: str | None = None,
        change_anchor: str | None = None,
        suggested_code: str | None = None,
    ) -> RefactorSuggestion:
        return RefactorSuggestion(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            file_path=changed_file.path.as_posix(),
            severity=severity,
            rationale=rationale,
            rule_reference=policy.id,
            evidence_scope=evidence_scope,
            change_anchor=change_anchor,
            impacted_symbol=changed_file.impacted_symbol.name if changed_file.impacted_symbol else None,
            suggested_code=suggested_code,
            is_safe_to_apply=False,
        )
