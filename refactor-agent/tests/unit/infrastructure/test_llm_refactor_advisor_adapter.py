from pathlib import Path
from types import SimpleNamespace

from app.domain.entities.changed_file import ChangedFile
from app.domain.entities.changed_symbol import ChangedSymbol
from app.domain.enums.change_type import ChangeType
from app.domain.enums.language import Language
from app.domain.enums.severity import Severity
from app.domain.value_objects.engineering_policy import EngineeringPolicy
from app.infrastructure.adapters.llm.llm_refactor_advisor_adapter import LlmRefactorAdvisorAdapter


class TestLlmRefactorAdvisorAdapter:
    def test_generates_python_advisory_suggestion_for_high_churn_file(self) -> None:
        adapter = LlmRefactorAdvisorAdapter(model="gpt-4o", api_key="")
        files = [
            ChangedFile(
                path=Path("app/service.py"),
                change_type=ChangeType.MODIFIED,
                language=Language.PYTHON,
                diff_content="diff",
                added_lines=30,
                removed_lines=12,
                context_snapshot="def run():\n    pass\n",
                symbol_context="def run():\n    pass\n",
                full_file_context="def helper():\n    return 1\n\ndef run():\n    pass\n",
                impacted_symbol=ChangedSymbol("run", "function", ChangeType.MODIFIED, "app/service.py", 3, 4),
            )
        ]
        policies = [
            EngineeringPolicy(
                id="python-refactor-safety",
                name="Python Refactor Safety",
                description="Keep refactors small.",
                applies_to=("*.py",),
                rules=({"type": "refactor", "instruction": "Refactor safely"},),
            )
        ]

        suggestions = adapter.advise(files, policies)

        assert suggestions
        assert suggestions[0].file_path == "app/service.py"
        assert suggestions[0].rule_reference == "python-refactor-safety"
        assert suggestions[0].is_safe_to_apply is False
        assert suggestions[0].evidence_scope == "changed-hunk+symbol+full-file"
        assert suggestions[0].impacted_symbol == "run"
        assert adapter.last_execution_mode == "fallback local"

    def test_generates_angular_component_advisory_suggestion(self) -> None:
        adapter = LlmRefactorAdvisorAdapter(model="gpt-4o", api_key="")
        files = [
            ChangedFile(
                path=Path("src/app/components/users/users.component.ts"),
                change_type=ChangeType.MODIFIED,
                language=Language.TYPESCRIPT,
                diff_content="diff",
                added_lines=18,
                removed_lines=10,
                context_snapshot="export class UsersComponent {}\n",
                symbol_context="export class UsersComponent {}\n",
                full_file_context="import { Component } from '@angular/core';\nexport class UsersComponent {}\n",
            )
        ]
        policies = [
            EngineeringPolicy(
                id="angular-refactor-safety",
                name="Angular Refactor Safety",
                description="Keep Angular refactors focused.",
                applies_to=("*.ts",),
                rules=({"type": "refactor", "instruction": "Keep refactors local"},),
            )
        ]

        suggestions = adapter.advise(files, policies)

        assert any(suggestion.title == "Reduce Angular component/service branching" for suggestion in suggestions)

    def test_flags_temporary_markers_as_warning(self) -> None:
        adapter = LlmRefactorAdvisorAdapter(model="gpt-4o", api_key="")
        files = [
            ChangedFile(
                path=Path("Core/RagSystem.Services.Documents/DocumentReader.cs"),
                change_type=ChangeType.MODIFIED,
                language=Language.CSHARP,
                diff_content="diff",
                added_lines=5,
                removed_lines=3,
                context_snapshot="// TODO: split this method\npublic class DocumentReader {}\n",
                symbol_context="public class DocumentReader {}\n",
                full_file_context="// TODO: split this method\npublic class DocumentReader {}\n",
            )
        ]
        policies = [
            EngineeringPolicy(
                id="csharp-refactor-safety",
                name="CSharp Refactor Safety",
                description="Keep refactors focused.",
                applies_to=("*.cs",),
                rules=({"type": "refactor", "instruction": "Keep refactors local"},),
            )
        ]

        suggestions = adapter.advise(files, policies)

        assert any(suggestion.severity == Severity.WARNING for suggestion in suggestions)

    def test_uses_full_file_context_to_detect_repeated_changed_symbol(self) -> None:
        adapter = LlmRefactorAdvisorAdapter(model="gpt-4o", api_key="")
        files = [
            ChangedFile(
                path=Path("app/service.py"),
                change_type=ChangeType.MODIFIED,
                language=Language.PYTHON,
                diff_content="diff",
                added_lines=4,
                removed_lines=0,
                context_snapshot="result = normalize_user(payload)\n",
                symbol_context=(
                    "def second(payload):\n    cached = normalize_user(payload)\n    return cached\n"
                ),
                full_file_context=(
                    "def first(payload):\n    return normalize_user(payload)\n\n"
                    "def second(payload):\n    cached = normalize_user(payload)\n    return cached\n"
                ),
                impacted_symbol=ChangedSymbol("second", "function", ChangeType.MODIFIED, "app/service.py", 3, 5),
            )
        ]
        policies = [
            EngineeringPolicy(
                id="python-refactor-safety",
                name="Python Refactor Safety",
                description="Keep refactors small.",
                applies_to=("*.py",),
                rules=({"type": "refactor", "instruction": "Refactor safely"},),
            )
        ]

        suggestions = adapter.advise(files, policies)

        repeated_logic = next(
            suggestion for suggestion in suggestions if suggestion.title == "Extract or reuse repeated logic in changed file"
        )
        assert repeated_logic.evidence_scope == "changed-hunk+symbol+full-file"
        assert repeated_logic.impacted_symbol == "second"
        assert repeated_logic.change_anchor == "normalize_user"

    def test_uses_repeated_changed_block_to_detect_duplication(self) -> None:
        adapter = LlmRefactorAdvisorAdapter(model="gpt-4o", api_key="")
        files = [
            ChangedFile(
                path=Path("app/service.py"),
                change_type=ChangeType.MODIFIED,
                language=Language.PYTHON,
                diff_content="diff",
                added_lines=6,
                removed_lines=0,
                context_snapshot=(
                    "normalized = normalize_user(payload)\n"
                    "return emit_result(normalized)\n"
                ),
                symbol_context=(
                    "def second(payload):\n"
                    "    normalized = normalize_user(payload)\n"
                    "    return emit_result(normalized)\n"
                ),
                full_file_context=(
                    "def first(payload):\n"
                    "    normalized = normalize_user(payload)\n"
                    "    return emit_result(normalized)\n\n"
                    "def second(payload):\n"
                    "    normalized = normalize_user(payload)\n"
                    "    return emit_result(normalized)\n"
                ),
                impacted_symbol=ChangedSymbol("second", "function", ChangeType.MODIFIED, "app/service.py", 4, 6),
            )
        ]
        policies = [
            EngineeringPolicy(
                id="python-refactor-safety",
                name="Python Refactor Safety",
                description="Keep refactors small.",
                applies_to=("*.py",),
                rules=({"type": "refactor", "instruction": "Refactor safely"},),
            )
        ]

        suggestions = adapter.advise(files, policies)

        repeated_logic = next(
            suggestion for suggestion in suggestions if suggestion.title == "Extract or reuse repeated logic in changed file"
        )
        assert repeated_logic.change_anchor == "normalized = normalize_user(payload)"
        assert repeated_logic.impacted_symbol == "second"

    def test_uses_openai_response_when_available(self) -> None:
        class _FakeResponses:
            def create(self, **_: object) -> SimpleNamespace:
                return SimpleNamespace(
                    output_text='{"suggestions":[{"title":"Extract query mapper","description":"Split mapping into a local helper.","rationale":"The changed method now mixes orchestration and mapping.","severity":"warning","change_anchor":"return mapper.Map(result)","suggested_code":"mapped = mapper.Map(result)\\nreturn mapped"}]}'
                )

        fake_client = SimpleNamespace(responses=_FakeResponses())
        adapter = LlmRefactorAdvisorAdapter(model="gpt-4o", api_key="test", client=fake_client)
        files = [
            ChangedFile(
                path=Path("app/service.py"),
                change_type=ChangeType.MODIFIED,
                language=Language.PYTHON,
                diff_content="diff",
                added_lines=6,
                removed_lines=2,
                context_snapshot="result = mapper.Map(source)\nreturn mapper.Map(result)\n",
                symbol_context="def run():\n    result = mapper.Map(source)\n    return mapper.Map(result)\n",
                full_file_context="def run():\n    result = mapper.Map(source)\n    return mapper.Map(result)\n",
                impacted_symbol=ChangedSymbol("run", "function", ChangeType.MODIFIED, "app/service.py", 1, 3),
            )
        ]
        policies = [
            EngineeringPolicy(
                id="python-refactor-safety",
                name="Python Refactor Safety",
                description="Keep refactors small.",
                applies_to=("*.py",),
                rules=({"type": "refactor", "instruction": "Refactor safely"},),
            )
        ]

        suggestions = adapter.advise(files, policies)

        assert len(suggestions) == 1
        assert suggestions[0].title == "Extract query mapper"
        assert suggestions[0].severity == Severity.WARNING
        assert suggestions[0].change_anchor == "return mapper.Map(result)"
        assert suggestions[0].suggested_code == "mapped = mapper.Map(result)\nreturn mapped"
        assert adapter.last_execution_mode == "LLM real"