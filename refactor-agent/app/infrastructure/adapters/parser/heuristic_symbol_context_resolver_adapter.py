import ast
import re
from dataclasses import dataclass
from pathlib import Path

from app.application.ports.outbound.symbol_context_resolver_port import SymbolContextResolverPort
from app.domain.entities.changed_file import ChangedFile
from app.domain.entities.changed_symbol import ChangedSymbol
from app.domain.enums.change_type import ChangeType
from app.domain.enums.language import Language
from app.domain.value_objects.symbol_context import SymbolContext

_PYTHON_SYMBOL_NODE_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
_OPEN_BRACE = "{"
_CLOSE_BRACE = "}"
_TS_CS_DECLARATION_RE = re.compile(
    r"^\s*(?:export\s+)?(?:public|private|protected|internal|static|async|sealed|abstract|partial|override|virtual|readonly\s+)*"
    r"(?:(?:[A-Za-z_]\w*(?:<[^>]+>)?(?:\[\])?\s+)+)?"
    r"(class|interface|record|enum|function|const|let|var|def|async\s+function|constructor|[A-Za-z_]\w*\s*\()"
)
_TS_DECORATOR_RE = re.compile(r"^\s*@\w+")


@dataclass(frozen=True)
class _OpenBraceSymbol:
    symbol: ChangedSymbol
    close_threshold: int
    owner_chain: tuple[str, ...]


class HeuristicSymbolContextResolverAdapter(SymbolContextResolverPort):
    """Resolve impacted symbol context using lightweight language heuristics."""

    def __init__(self, max_context_chars: int = 4000) -> None:
        self._max_context_chars = max_context_chars

    def resolve(self, changed_file: ChangedFile, file_content: str) -> SymbolContext:
        target_lines = self._extract_target_lines(changed_file)
        if not target_lines or not file_content.strip():
            return SymbolContext()

        if changed_file.language == Language.PYTHON:
            return self._resolve_python_symbol(changed_file, file_content, target_lines)

        if changed_file.language in {Language.CSHARP, Language.TYPESCRIPT}:
            return self._resolve_brace_language_symbol(changed_file, file_content, target_lines)

        return SymbolContext()

    def _resolve_python_symbol(
        self,
        changed_file: ChangedFile,
        file_content: str,
        target_lines: tuple[int, ...],
    ) -> SymbolContext:
        try:
            module = ast.parse(file_content)
        except SyntaxError:
            return SymbolContext()

        match: ast.AST | None = None
        for node in ast.walk(module):
            if not isinstance(node, _PYTHON_SYMBOL_NODE_TYPES):
                continue
            start_line = getattr(node, "lineno", None)
            end_line = getattr(node, "end_lineno", None)
            if start_line is None or end_line is None:
                continue
            overlap = sum(1 for target_line in target_lines if start_line <= target_line <= end_line)
            if overlap > 0:
                if match is None or self._is_better_python_match(match, node, target_lines):
                    match = node

        if match is None:
            return SymbolContext()

        symbol_type = "class" if isinstance(match, ast.ClassDef) else "function"
        symbol = ChangedSymbol(
            name=getattr(match, "name", "<anonymous>"),
            symbol_type=symbol_type,
            change_type=changed_file.change_type,
            file_path=changed_file.path.as_posix(),
            start_line=match.lineno,
            end_line=getattr(match, "end_lineno", match.lineno),
        )
        snippet = self._slice_lines(file_content, symbol.start_line, symbol.end_line)
        return SymbolContext(symbol=symbol, snippet=snippet)

    def _resolve_brace_language_symbol(
        self,
        changed_file: ChangedFile,
        file_content: str,
        target_lines: tuple[int, ...],
    ) -> SymbolContext:
        lines = file_content.splitlines()
        declarations = self._collect_brace_language_declarations(lines, changed_file)
        containing = [
            item
            for item in declarations
            if any(item.start_line <= target_line <= item.end_line for target_line in target_lines)
        ]
        if not containing:
            return SymbolContext()

        symbol = min(
            containing,
            key=lambda item: (-self._changed_line_overlap(item, target_lines), item.end_line - item.start_line),
        )
        symbol = self._qualify_selected_member_symbol(symbol, containing)
        snippet = self._slice_lines(file_content, symbol.start_line, symbol.end_line)
        return SymbolContext(symbol=symbol, snippet=snippet)

    def _collect_brace_language_declarations(
        self,
        lines: list[str],
        changed_file: ChangedFile,
    ) -> list[ChangedSymbol]:
        declarations: list[ChangedSymbol] = []
        stack: list[_OpenBraceSymbol] = []
        brace_depth = 0
        decorator_start_line: int | None = None
        pending_symbol: ChangedSymbol | None = None

        for index, raw_line in enumerate(lines, start=1):
            stripped = raw_line.strip()
            decorator_start_line = self._update_decorator_start(
                changed_file.language,
                stripped,
                index,
                decorator_start_line,
            )
            if pending_symbol is None:
                pending_symbol = self._build_pending_symbol(
                    changed_file,
                    index,
                    stripped,
                    stack,
                    decorator_start_line,
                )

            opens = raw_line.count(_OPEN_BRACE)
            closes = raw_line.count(_CLOSE_BRACE)
            pending_symbol, decorator_start_line = self._register_pending_symbol(
                pending_symbol,
                stripped,
                stack,
                declarations,
                brace_depth,
                opens,
                decorator_start_line,
                changed_file.language,
            )

            brace_depth += opens

            while stack and brace_depth < stack[-1].close_threshold:
                open_symbol = stack.pop()
                declarations.append(self._complete_symbol(open_symbol.symbol, index))

            brace_depth -= closes
            if brace_depth < 0:
                brace_depth = 0

        while stack:
            open_symbol = stack.pop()
            declarations.append(self._complete_symbol(open_symbol.symbol, len(lines)))

        return declarations

    def _build_pending_symbol(
        self,
        changed_file: ChangedFile,
        line_number: int,
        stripped_line: str,
        stack: list[_OpenBraceSymbol],
        decorator_start_line: int | None,
    ) -> ChangedSymbol | None:
        if self._looks_like_class_declaration(stripped_line):
            start_line = decorator_start_line or line_number
            base_name = self._extract_named_symbol(stripped_line, fallback=Path(changed_file.path).stem)
            qualified_name = self._qualify_name(stack, base_name)
            return ChangedSymbol(
                name=qualified_name,
                symbol_type="class",
                change_type=changed_file.change_type,
                file_path=changed_file.path.as_posix(),
                start_line=start_line,
                end_line=line_number,
            )

        if self._looks_like_method_or_function(stripped_line):
            base_name = self._extract_method_name(stripped_line)
            owner_chain = self._current_owner_names(stack)
            symbol_type = self._resolve_member_symbol_type(base_name, owner_chain)
            return ChangedSymbol(
                name=self._qualify_member_name(base_name, owner_chain),
                symbol_type=symbol_type,
                change_type=changed_file.change_type,
                file_path=changed_file.path.as_posix(),
                start_line=line_number,
                end_line=line_number,
            )

        return None

    def _complete_symbol(self, symbol: ChangedSymbol, end_line: int) -> ChangedSymbol:
        return ChangedSymbol(
            name=symbol.name,
            symbol_type=symbol.symbol_type,
            change_type=symbol.change_type,
            file_path=symbol.file_path,
            start_line=symbol.start_line,
            end_line=end_line,
        )

    def _extract_target_lines(self, changed_file: ChangedFile) -> tuple[int, ...]:
        if changed_file.changed_line_numbers:
            return changed_file.changed_line_numbers

        diff_content = changed_file.diff_content
        for line in diff_content.splitlines():
            if not line.startswith("@@"):
                continue
            match = re.search(r"\+(\d+)", line)
            if match:
                return (int(match.group(1)),)
        return ()

    def _is_better_python_match(
        self,
        current_match: ast.AST,
        candidate_match: ast.AST,
        target_lines: tuple[int, ...],
    ) -> bool:
        current_overlap = self._python_overlap(current_match, target_lines)
        candidate_overlap = self._python_overlap(candidate_match, target_lines)
        if candidate_overlap != current_overlap:
            return candidate_overlap > current_overlap
        current_size = getattr(current_match, "end_lineno") - getattr(current_match, "lineno")
        candidate_size = getattr(candidate_match, "end_lineno") - getattr(candidate_match, "lineno")
        return candidate_size < current_size

    def _python_overlap(self, node: ast.AST, target_lines: tuple[int, ...]) -> int:
        start_line = getattr(node, "lineno", 0)
        end_line = getattr(node, "end_lineno", 0)
        return sum(1 for target_line in target_lines if start_line <= target_line <= end_line)

    def _changed_line_overlap(self, symbol: ChangedSymbol, target_lines: tuple[int, ...]) -> int:
        return sum(1 for target_line in target_lines if symbol.start_line <= target_line <= symbol.end_line)

    def _looks_like_class_declaration(self, stripped_line: str) -> bool:
        return bool(
            re.match(
                r"^(?:export\s+)?(?:(?:public|private|protected|internal|abstract|sealed|partial)\s+)*(class|interface|record|enum)\s+",
                stripped_line,
            )
        )

    def _looks_like_method_or_function(self, stripped_line: str) -> bool:
        if stripped_line.startswith(("if ", "for ", "while ", "switch ", "catch ", "return ")):
            return False
        if stripped_line.startswith("def ") or stripped_line.startswith("async def "):
            return True
        if "(" not in stripped_line:
            return False
        return bool(_TS_CS_DECLARATION_RE.match(stripped_line))

    def _extract_named_symbol(self, stripped_line: str, fallback: str) -> str:
        match = re.search(r"(?:class|interface|record|enum)\s+([A-Za-z_]\w*)", stripped_line)
        return match.group(1) if match else fallback

    def _extract_method_name(self, stripped_line: str) -> str:
        python_match = re.search(r"(?:async\s+def|def)\s+([A-Za-z_]\w*)", stripped_line)
        if python_match:
            return python_match.group(1)

        constructor_match = re.search(r"\bconstructor\s*\(", stripped_line)
        if constructor_match:
            return "constructor"

        name_match = re.search(r"([A-Za-z_]\w*)\s*\(", stripped_line)
        if name_match:
            return name_match.group(1)
        return "<anonymous>"

    def _is_decorator_line(self, language: Language, stripped_line: str) -> bool:
        return language == Language.TYPESCRIPT and bool(_TS_DECORATOR_RE.match(stripped_line))

    def _current_owner_names(self, stack: list[_OpenBraceSymbol]) -> tuple[str, ...]:
        class_symbols = [open_symbol.symbol.name for open_symbol in stack if open_symbol.symbol.symbol_type == "class"]
        if not class_symbols:
            return ()
        return tuple(class_symbols[-1].split("."))

    def _owner_chain_for(
        self,
        stack: list[_OpenBraceSymbol],
        symbol: ChangedSymbol,
    ) -> tuple[str, ...]:
        if symbol.symbol_type == "class":
            return self._current_owner_names(stack) + (symbol.name,)
        return self._current_owner_names(stack)

    def _qualify_name(self, stack: list[_OpenBraceSymbol], base_name: str) -> str:
        owner_names = self._current_owner_names(stack)
        if not owner_names:
            return base_name
        return ".".join((*owner_names, base_name))

    def _qualify_member_name(self, base_name: str, owner_names: tuple[str, ...]) -> str:
        if not owner_names:
            return base_name
        if base_name == "constructor":
            return ".".join((*owner_names, owner_names[-1]))
        return ".".join((*owner_names, base_name))

    def _resolve_member_symbol_type(self, base_name: str, owner_names: tuple[str, ...]) -> str:
        if owner_names and (base_name == "constructor" or base_name == owner_names[-1].split(".")[-1]):
            return "constructor"
        return "method" if owner_names else "function"

    def _slice_lines(self, file_content: str, start_line: int, end_line: int) -> str:
        lines = file_content.splitlines()
        snippet = "\n".join(lines[start_line - 1 : end_line]).strip()
        if len(snippet) <= self._max_context_chars:
            return snippet
        return snippet[: self._max_context_chars] + "\n... [truncated]"

    def _qualify_selected_member_symbol(
        self,
        symbol: ChangedSymbol,
        containing_symbols: list[ChangedSymbol],
    ) -> ChangedSymbol:
        if symbol.symbol_type not in {"method", "constructor", "function"} or "." in symbol.name:
            return symbol

        owning_classes = [
            candidate
            for candidate in containing_symbols
            if candidate.symbol_type == "class"
            and candidate.start_line <= symbol.start_line <= candidate.end_line
        ]
        if not owning_classes:
            return symbol

        owning_class = min(owning_classes, key=lambda item: item.end_line - item.start_line)
        qualified_name = f"{owning_class.name}.{symbol.name}"
        symbol_type = "constructor" if symbol.symbol_type == "constructor" else "method"
        return ChangedSymbol(
            name=qualified_name,
            symbol_type=symbol_type,
            change_type=symbol.change_type,
            file_path=symbol.file_path,
            start_line=symbol.start_line,
            end_line=symbol.end_line,
        )

    def _update_decorator_start(
        self,
        language: Language,
        stripped_line: str,
        line_number: int,
        current_start: int | None,
    ) -> int | None:
        if self._is_decorator_line(language, stripped_line):
            return current_start or line_number
        if language == Language.TYPESCRIPT and current_start is not None and not self._looks_like_class_declaration(stripped_line):
            return current_start
        return current_start

    def _register_pending_symbol(
        self,
        pending_symbol: ChangedSymbol | None,
        stripped_line: str,
        stack: list[_OpenBraceSymbol],
        declarations: list[ChangedSymbol],
        brace_depth: int,
        opens: int,
        decorator_start_line: int | None,
        language: Language,
    ) -> tuple[ChangedSymbol | None, int | None]:
        if pending_symbol is not None:
            if opens > 0:
                owner_chain = self._owner_chain_for(stack, pending_symbol)
                stack.append(
                    _OpenBraceSymbol(
                        symbol=pending_symbol,
                        close_threshold=brace_depth + opens,
                        owner_chain=owner_chain,
                    )
                )
                return None, None
            if stripped_line.endswith(";"):
                declarations.append(pending_symbol)
                return None, None
            if stripped_line and stripped_line != _OPEN_BRACE:
                return pending_symbol, decorator_start_line
            return pending_symbol, decorator_start_line

        if stripped_line and not self._is_decorator_line(language, stripped_line):
            return None, decorator_start_line
        return None, decorator_start_line