from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class GitHubContextProviderPort(ABC):
    """Outbound port — reads GitHub Actions runtime context (env vars, event payload).

    Isolates the application layer from direct environment variable access so that
    the entrypoints and use cases remain testable without setting up a real CI env.
    """

    @abstractmethod
    def get_base_ref(self) -> str:
        ...

    @abstractmethod
    def get_base_branch(self) -> str:
        ...

    @abstractmethod
    def get_head_ref(self) -> str:
        ...

    @abstractmethod
    def get_head_branch(self) -> str:
        ...

    @abstractmethod
    def get_repository(self) -> str:
        ...

    @abstractmethod
    def get_pull_request_number(self) -> Optional[int]:
        ...

    @abstractmethod
    def get_event_payload(self) -> Dict[str, Any]:
        ...
