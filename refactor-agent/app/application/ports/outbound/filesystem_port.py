from abc import ABC, abstractmethod
from pathlib import Path


class FileSystemPort(ABC):
    """Outbound port — abstracts local filesystem read/write operations."""

    @abstractmethod
    def read_file(self, path: Path) -> str:
        ...

    @abstractmethod
    def write_file(self, path: Path, content: str) -> None:
        ...

    @abstractmethod
    def file_exists(self, path: Path) -> bool:
        ...
