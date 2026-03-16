from abc import ABC, abstractmethod

from app.domain.value_objects.repository_prompt_guidance import RepositoryPromptGuidance


class RepositoryPromptGuidancePort(ABC):
    """Outbound port — loads repository-specific prompt guidance for LLM stages."""

    @abstractmethod
    def load(self, repo_path: str, profile_name: str | None = None) -> RepositoryPromptGuidance | None:
        ...