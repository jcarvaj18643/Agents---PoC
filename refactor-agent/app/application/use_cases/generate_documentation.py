from typing import List

from app.application.ports.outbound.llm_documentation_generator_port import (
    LlmDocumentationGeneratorPort,
)
from app.domain.entities.changed_file import ChangedFile
from app.domain.entities.documentation_artifact import DocumentationArtifact
from app.domain.value_objects.engineering_policy import EngineeringPolicy


class GenerateDocumentationUseCase:
    """Use case: produce documentation artifacts from changed files via an LLM.

    Pre-processing (chunking, context trimming) and post-processing
    (formatting, deduplication) will be added here before the LLM call.
    """

    def __init__(self, llm_doc_generator: LlmDocumentationGeneratorPort) -> None:
        self._llm_doc_generator = llm_doc_generator
        self.last_execution_mode = "not-invoked"

    def execute(
        self,
        files: List[ChangedFile],
        policies: List[EngineeringPolicy],
    ) -> List[DocumentationArtifact]:
        if not files:
            self.last_execution_mode = "not-invoked"
            return []

        # TODO: pre-process files (token budget management, chunking)
        # TODO: post-process LLM output (validation, formatting)
        artifacts = self._llm_doc_generator.generate(files, policies)
        self.last_execution_mode = getattr(self._llm_doc_generator, "last_execution_mode", "unknown")
        return artifacts
