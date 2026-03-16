from typing import Dict, List

from app.domain.entities.changed_file import ChangedFile
from app.domain.entities.code_scope import CodeScope
from app.domain.enums.language import Language


class ScopeAnalyzerService:
    """Domain service that computes analysis metrics and projections over a CodeScope.

    Pure domain logic — no I/O, no framework dependencies.
    """

    def count_by_language(self, scope: CodeScope) -> Dict[Language, int]:
        """Count changed files grouped by detected language."""
        counts: Dict[Language, int] = {}
        for f in scope.changed_files:
            counts[f.language] = counts.get(f.language, 0) + 1
        return counts

    def filter_by_language(
        self, scope: CodeScope, language: Language
    ) -> List[ChangedFile]:
        """Return only the files matching a specific language."""
        return [f for f in scope.changed_files if f.language == language]

    def is_trivial(self, scope: CodeScope, threshold: int = 5) -> bool:
        """Return True when the scope has fewer changed files than *threshold*.

        Trivial scopes may skip expensive LLM calls in future optimisations.
        """
        return scope.total_files < threshold
