from abc import ABC, abstractmethod

from app.domain.entities.code_scope import CodeScope


class GitDiffReaderPort(ABC):
    """Outbound port — reads the diff between two git refs and returns a CodeScope."""

    @abstractmethod
    def read_diff(self, base_ref: str, head_ref: str, repo_path: str) -> CodeScope:
        ...
