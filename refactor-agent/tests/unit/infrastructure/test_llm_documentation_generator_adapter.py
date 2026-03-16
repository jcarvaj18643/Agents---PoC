from pathlib import Path
from types import SimpleNamespace

from app.domain.entities.changed_file import ChangedFile
from app.domain.entities.changed_symbol import ChangedSymbol
from app.domain.enums.change_type import ChangeType
from app.domain.enums.language import Language
from app.domain.value_objects.engineering_policy import EngineeringPolicy
from app.infrastructure.adapters.llm.llm_documentation_generator_adapter import (
    LlmDocumentationGeneratorAdapter,
)


class TestLlmDocumentationGeneratorAdapter:
    def test_falls_back_when_no_api_key_is_configured(self) -> None:
        adapter = LlmDocumentationGeneratorAdapter(model="gpt-4o", api_key="")
        files = [
            ChangedFile(
                path=Path("app/service.py"),
                change_type=ChangeType.MODIFIED,
                language=Language.PYTHON,
                diff_content="diff",
                impacted_symbol=ChangedSymbol("run", "function", ChangeType.MODIFIED, "app/service.py", 1, 3),
            )
        ]

        artifacts = adapter.generate(files, [])

        assert len(artifacts) == 1
        assert artifacts[0].tokens_used == 0
        assert "Impacted symbol: `run`" in artifacts[0].generated_content
        assert adapter.last_execution_mode == "fallback local"

    def test_uses_openai_response_when_available(self) -> None:
        captured_inputs: list[str] = []

        class _FakeResponses:
            def create(self, **kwargs: object) -> SimpleNamespace:
                captured_inputs.append(str(kwargs.get("input", "")))
                return SimpleNamespace(
                    output_text="# Summary\n\nUpdated docs for the changed service.",
                    usage=SimpleNamespace(total_tokens=123),
                )

        fake_client = SimpleNamespace(responses=_FakeResponses())
        adapter = LlmDocumentationGeneratorAdapter(model="gpt-4o", api_key="test", client=fake_client)
        files = [
            ChangedFile(
                path=Path("app/service.py"),
                change_type=ChangeType.MODIFIED,
                language=Language.PYTHON,
                diff_content="diff",
                context_snapshot="def run():\n    return 1\n",
                symbol_context="def run():\n    return 1\n",
                full_file_context="def run():\n    return 1\n",
                repository_guidance="Architecture: Hexagonal\nLayer conventions:\n- persistence folder is src/Persistence",
                impacted_symbol=ChangedSymbol("run", "function", ChangeType.MODIFIED, "app/service.py", 1, 2),
            )
        ]
        policies = [
            EngineeringPolicy(
                id="python-docs",
                name="Python Docs",
                description="Document changed Python code.",
                applies_to=("*.py",),
                rules=({"type": "documentation", "instruction": "Add docs"},),
            )
        ]

        artifacts = adapter.generate(files, policies)

        assert len(artifacts) == 1
        assert artifacts[0].generated_content.startswith("# Summary")
        assert artifacts[0].tokens_used == 123
        assert "Repository guidance:" in captured_inputs[0]
        assert "Architecture: Hexagonal" in captured_inputs[0]
        assert adapter.last_execution_mode == "LLM real"