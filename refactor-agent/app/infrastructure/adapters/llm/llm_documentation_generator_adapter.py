from datetime import datetime, timezone
from typing import Any, List

from openai import OpenAI

from app.application.ports.outbound.llm_documentation_generator_port import (
    LlmDocumentationGeneratorPort,
)
from app.domain.entities.changed_file import ChangedFile
from app.domain.entities.documentation_artifact import DocumentationArtifact
from app.domain.value_objects.engineering_policy import EngineeringPolicy
from app.infrastructure.logging.console_logger import get_logger
from app.infrastructure.adapters.llm.openai_response_utils import (
    extract_output_text,
    extract_usage_tokens,
)

logger = get_logger(__name__)

_EMPTY_CONTEXT = "<empty>"
_LLM_MODE_REAL = "LLM real"
_LLM_MODE_FALLBACK = "fallback local"


class LlmDocumentationGeneratorAdapter(LlmDocumentationGeneratorPort):
    """Adapter: calls an LLM API to produce documentation for changed files.

    Uses a real OpenAI-compatible client when credentials are available and
    falls back to deterministic local output when they are not.
    """

    def __init__(self, model: str, api_key: str, client: Any | None = None) -> None:
        self._model = model
        self._api_key = api_key
        self._client = client or (OpenAI(api_key=api_key) if api_key else None)
        self.last_execution_mode = "not-invoked"

    def generate(
        self,
        files: List[ChangedFile],
        policies: List[EngineeringPolicy],
    ) -> List[DocumentationArtifact]:
        if not files:
            self.last_execution_mode = "not-invoked"
            return []

        if self._client is None:
            self.last_execution_mode = _LLM_MODE_FALLBACK
            logger.info(
                "Documentation generator mode: %s [reason=no_api_key, files=%d, model=%s]",
                _LLM_MODE_FALLBACK,
                len(files),
                self._model,
            )
            return [self._build_fallback_artifact(changed_file) for changed_file in files]

        execution_modes: list[str] = []
        logger.info(
            "Documentation generator mode: %s [files=%d, model=%s]",
            _LLM_MODE_REAL,
            len(files),
            self._model,
        )
        artifacts: list[DocumentationArtifact] = []
        for changed_file in files:
            try:
                response = self._client.responses.create(
                    model=self._model,
                    input=self._build_prompt(changed_file, policies),
                )
                content = extract_output_text(response) or self._build_fallback_content(changed_file)
                artifacts.append(
                    DocumentationArtifact(
                        file_path=changed_file.path,
                        generated_content=content,
                        generated_at=datetime.now(timezone.utc),
                        model_used=self._model,
                        tokens_used=extract_usage_tokens(response),
                    )
                )
                logger.info(
                    "Documentation artifact generated with %s [file=%s, model=%s, tokens=%d]",
                    _LLM_MODE_REAL,
                    changed_file.path,
                    self._model,
                    artifacts[-1].tokens_used,
                )
                execution_modes.append(_LLM_MODE_REAL)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Documentation generator switched to %s for %s after OpenAI error: %s",
                    _LLM_MODE_FALLBACK,
                    changed_file.path,
                    exc,
                )
                artifacts.append(self._build_fallback_artifact(changed_file))
                execution_modes.append(_LLM_MODE_FALLBACK)
        self.last_execution_mode = self._summarize_execution_modes(execution_modes)
        return artifacts

    def _build_prompt(self, changed_file: ChangedFile, policies: List[EngineeringPolicy]) -> str:
        policy_lines = [f"- {policy.name}: {policy.description}" for policy in policies]
        symbol_name = changed_file.impacted_symbol.name if changed_file.impacted_symbol else "n/a"
        return "\n".join(
            [
                "You are documenting a changed source file for an engineering governance agent.",
                "Generate concise markdown documentation focused on the changed area.",
                "Include: purpose, impacted symbol, change summary, and refactor/testing notes when justified.",
                "Do not invent APIs or behavior not supported by the provided context.",
                "Repository guidance:",
                changed_file.repository_guidance or "No repository-specific guidance provided.",
                f"File: {changed_file.path.as_posix()}",
                f"Impacted symbol: {symbol_name}",
                "Policies:",
                *(policy_lines or ["- No documentation-specific policy provided."]),
                "Changed hunk context:",
                changed_file.changed_hunk_context or _EMPTY_CONTEXT,
                "Symbol context:",
                changed_file.symbol_context or _EMPTY_CONTEXT,
                "Full file context:",
                changed_file.full_file_context or _EMPTY_CONTEXT,
            ]
        )

    def _build_fallback_artifact(self, changed_file: ChangedFile) -> DocumentationArtifact:
        return DocumentationArtifact(
            file_path=changed_file.path,
            generated_content=self._build_fallback_content(changed_file),
            generated_at=datetime.now(timezone.utc),
            model_used=self._model,
            tokens_used=0,
        )

    def _build_fallback_content(self, changed_file: ChangedFile) -> str:
        symbol_name = changed_file.impacted_symbol.name if changed_file.impacted_symbol else changed_file.path.stem
        return (
            f"# Documentation for `{changed_file.path.name}`\n\n"
            f"- Impacted symbol: `{symbol_name}`\n"
            f"- Summary: changed area captured for governance review.\n"
        )

    def _summarize_execution_modes(self, execution_modes: list[str]) -> str:
        if not execution_modes:
            return "not-invoked"
        unique_modes = set(execution_modes)
        if len(unique_modes) == 1:
            return execution_modes[0]
        return "mixed"
