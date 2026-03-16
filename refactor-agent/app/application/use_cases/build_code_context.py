from pathlib import Path
from typing import List

from app.application.ports.outbound.filesystem_port import FileSystemPort
from app.application.ports.outbound.symbol_context_resolver_port import SymbolContextResolverPort
from app.domain.entities.changed_file import ChangedFile
from app.domain.entities.code_scope import CodeScope


class BuildCodeContextUseCase:
    """Use case: enrich changed files with dual context for downstream consumers.

    Phase 6.1 keeps activation strictly diff-scoped while allowing richer
    reasoning on each changed file. Downstream steps receive both a changed-hunk
    view and a full-file view for the same changed file, so recommendations can
    stay anchored to the change without being blind to local duplication or
    existing helpers elsewhere in that file.
    """

    def __init__(
        self,
        filesystem: FileSystemPort,
        symbol_context_resolver: SymbolContextResolverPort | None = None,
        max_context_chars: int = 4000,
    ) -> None:
        self._filesystem = filesystem
        self._symbol_context_resolver = symbol_context_resolver
        self._max_context_chars = max_context_chars

    def execute(self, scope: CodeScope, repo_path: str) -> List[ChangedFile]:
        enriched_files: List[ChangedFile] = []
        root = Path(repo_path)

        for changed_file in scope.changed_files:
            absolute_path = root / changed_file.path
            full_file_context = ""
            symbol_context = ""
            impacted_symbol = None
            if self._filesystem.file_exists(absolute_path):
                full_file_contents = self._filesystem.read_file(absolute_path)
                full_file_context = self._truncate_content(full_file_contents)
                if self._symbol_context_resolver is not None:
                    resolved_symbol_context = self._symbol_context_resolver.resolve(changed_file, full_file_contents)
                    symbol_context = self._truncate_content(resolved_symbol_context.snippet)
                    impacted_symbol = resolved_symbol_context.symbol

            context_snapshot = self._build_diff_scoped_context(changed_file.diff_content)

            if not context_snapshot:
                context_snapshot = full_file_context
            if not symbol_context:
                symbol_context = full_file_context

            enriched_files.append(
                ChangedFile(
                    path=changed_file.path,
                    change_type=changed_file.change_type,
                    language=changed_file.language,
                    diff_content=changed_file.diff_content,
                    added_lines=changed_file.added_lines,
                    removed_lines=changed_file.removed_lines,
                    changed_line_numbers=changed_file.changed_line_numbers,
                    context_snapshot=context_snapshot,
                    full_file_context=full_file_context,
                    symbol_context=symbol_context,
                    impacted_symbol=impacted_symbol,
                )
            )

        return enriched_files

    def _build_diff_scoped_context(self, diff_content: str) -> str:
        hunk_lines: list[str] = []
        in_hunk = False

        for raw_line in diff_content.splitlines():
            if raw_line.startswith("@@"):
                in_hunk = True
                hunk_lines.append(raw_line)
                continue

            if not in_hunk:
                continue

            if raw_line.startswith("+++") or raw_line.startswith("---"):
                continue

            if raw_line.startswith("+"):
                hunk_lines.append(raw_line[1:])
                continue

            if raw_line.startswith(" "):
                hunk_lines.append(raw_line[1:])

        if not hunk_lines:
            return ""
        return self._truncate_content("\n".join(hunk_lines).strip())

    def _truncate_content(self, content: str) -> str:
        if len(content) <= self._max_context_chars:
            return content
        return content[: self._max_context_chars] + "\n... [truncated]"
