from abc import ABC, abstractmethod

from app.domain.entities.changed_file import ChangedFile
from app.domain.value_objects.symbol_context import SymbolContext


class SymbolContextResolverPort(ABC):
    """Outbound port — resolves impacted symbol context for a changed file."""

    @abstractmethod
    def resolve(self, changed_file: ChangedFile, file_content: str) -> SymbolContext:
        ...