from pathlib import Path

from app.application.use_cases.generate_refactor_suggestions import GenerateRefactorSuggestionsUseCase
from app.domain.entities.changed_file import ChangedFile
from app.domain.entities.refactor_suggestion import RefactorSuggestion
from app.domain.enums.change_type import ChangeType
from app.domain.enums.language import Language
from app.domain.enums.severity import Severity
from app.domain.value_objects.engineering_policy import EngineeringPolicy


class _FakeAdvisor:
    def __init__(
        self,
        suggestions_by_file: dict[str, list[RefactorSuggestion]],
        mode_by_file: dict[str, str] | None = None,
    ) -> None:
        self._suggestions_by_file = suggestions_by_file
        self._mode_by_file = mode_by_file or {}
        self.calls: list[tuple[list[str], list[str]]] = []
        self.last_execution_mode = "not-invoked"

    def advise(self, files, policies):  # type: ignore[no-untyped-def]
        file_paths = [file.path.as_posix() for file in files]
        self.calls.append((file_paths, [policy.id for policy in policies]))
        self.last_execution_mode = self._mode_by_file.get(file_paths[0], "fallback local")
        return self._suggestions_by_file.get(file_paths[0], [])


class TestGenerateRefactorSuggestionsUseCase:
    def test_filters_policies_by_refactor_rule_and_file_glob(self) -> None:
        files = [
            ChangedFile(Path("app/service.py"), ChangeType.MODIFIED, Language.PYTHON, "", added_lines=10),
            ChangedFile(Path("README.md"), ChangeType.MODIFIED, Language.UNKNOWN, "", added_lines=2),
        ]
        advisor = _FakeAdvisor({"app/service.py": []})
        policies = [
            EngineeringPolicy(
                id="python-refactor",
                name="Python Refactor",
                description="Refactor Python files",
                applies_to=("*.py",),
                rules=({"type": "refactor", "instruction": "Refactor safely"},),
            ),
            EngineeringPolicy(
                id="python-docs",
                name="Python Docs",
                description="Document Python files",
                applies_to=("*.py",),
                rules=({"type": "documentation", "instruction": "Add docs"},),
            ),
        ]

        use_case = GenerateRefactorSuggestionsUseCase(advisor)
        suggestions = use_case.execute(files, policies)

        assert suggestions == []
        assert advisor.calls == [(["app/service.py"], ["python-refactor"])]
        assert use_case.last_execution_mode == "fallback local"

    def test_deduplicates_and_ranks_suggestions(self) -> None:
        duplicate_one = RefactorSuggestion(
            id="1",
            title="Same suggestion",
            description="A",
            file_path="app/service.py",
            severity=Severity.INFO,
            rationale="A",
            rule_reference="python-refactor",
            impacted_symbol="service.run",
        )
        duplicate_two = RefactorSuggestion(
            id="2",
            title="Same suggestion",
            description="B",
            file_path="app/service.py",
            severity=Severity.WARNING,
            rationale="B",
            rule_reference="python-refactor",
            impacted_symbol="service.run",
        )
        critical = RefactorSuggestion(
            id="3",
            title="Higher priority",
            description="C",
            file_path="app/service.py",
            severity=Severity.CRITICAL,
            rationale="C",
            rule_reference="python-refactor",
            impacted_symbol="service.run",
        )
        files = [ChangedFile(Path("app/service.py"), ChangeType.MODIFIED, Language.PYTHON, "")]
        advisor = _FakeAdvisor({"app/service.py": [duplicate_one, duplicate_two, critical]})
        policies = [
            EngineeringPolicy(
                id="python-refactor",
                name="Python Refactor",
                description="Refactor Python files",
                applies_to=("*.py",),
                rules=({"type": "refactor", "instruction": "Refactor safely"},),
            )
        ]

        use_case = GenerateRefactorSuggestionsUseCase(advisor)
        suggestions = use_case.execute(files, policies)

        assert [(suggestion.title, suggestion.severity) for suggestion in suggestions] == [
            ("Higher priority", Severity.CRITICAL),
            ("Same suggestion", Severity.WARNING),
        ]
        assert use_case.last_execution_mode == "fallback local"

    def test_marks_stage_as_not_invoked_when_no_refactor_policies_apply(self) -> None:
        files = [ChangedFile(Path("README.md"), ChangeType.MODIFIED, Language.UNKNOWN, "")]
        advisor = _FakeAdvisor({})
        policies = [
            EngineeringPolicy(
                id="docs-only",
                name="Docs Only",
                description="Documentation only.",
                applies_to=("*.md",),
                rules=({"type": "documentation", "instruction": "Document changes"},),
            )
        ]

        use_case = GenerateRefactorSuggestionsUseCase(advisor)

        suggestions = use_case.execute(files, policies)

        assert suggestions == []
        assert advisor.calls == []
        assert use_case.last_execution_mode == "not-invoked"

    def test_filters_low_signal_test_suggestions_without_traceable_anchor(self) -> None:
        files = [ChangedFile(Path("tests/test_service.py"), ChangeType.MODIFIED, Language.PYTHON, "")]
        advisor = _FakeAdvisor(
            {
                "tests/test_service.py": [
                    RefactorSuggestion(
                        id="1",
                        title="Break up high-churn change",
                        description="A",
                        file_path="tests/test_service.py",
                        severity=Severity.INFO,
                        rationale="A",
                        rule_reference="python-refactor",
                        change_anchor="change-1",
                    ),
                    RefactorSuggestion(
                        id="2",
                        title="Keep focused fixture intent",
                        description="B",
                        file_path="tests/test_service.py",
                        severity=Severity.WARNING,
                        rationale="B",
                        rule_reference="python-refactor",
                        impacted_symbol="test_service_behavior",
                    ),
                ]
            }
        )
        policies = [
            EngineeringPolicy(
                id="python-refactor",
                name="Python Refactor",
                description="Refactor Python files",
                applies_to=("*.py",),
                rules=({"type": "refactor", "instruction": "Refactor safely"},),
            )
        ]

        use_case = GenerateRefactorSuggestionsUseCase(advisor)

        suggestions = use_case.execute(files, policies)

        assert [suggestion.title for suggestion in suggestions] == ["Keep focused fixture intent"]