from pathlib import Path

from app.application.ports.outbound.filesystem_port import FileSystemPort
from app.infrastructure.logging.console_logger import get_logger

logger = get_logger(__name__)


class FileSystemAdapter(FileSystemPort):
    """Adapter: performs local filesystem reads and writes.

    Wraps pathlib calls and enforces UTF-8 encoding throughout.
    """

    def read_file(self, path: Path) -> str:
        logger.debug("Reading file: %s", path)
        return path.read_text(encoding="utf-8")

    def write_file(self, path: Path, content: str) -> None:
        logger.debug("Writing file: %s", path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def file_exists(self, path: Path) -> bool:
        return path.exists()
