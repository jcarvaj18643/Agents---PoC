import re
from pathlib import Path
from typing import List, Optional

from app.domain.entities.changed_file import ChangedFile
from app.domain.enums.change_type import ChangeType
from app.domain.enums.language import Language


class DiffParser:
    """Translates raw unified-diff text into a list of ChangedFile domain entities.

    Single responsibility: low-level text parsing only. No I/O, no subprocess calls.
    The concrete git invocation lives in GitDiffReaderAdapter.
    """

    def parse(self, raw_diff: str) -> List[ChangedFile]:
      """Parse a unified diff string into ChangedFile objects."""
      if not raw_diff.strip():
        return []

      changed_files: List[ChangedFile] = []
      current_block: List[str] = []

      for line in raw_diff.splitlines(keepends=True):
        if line.startswith("diff --git ") and current_block:
          parsed_file = self._parse_block(current_block)
          if parsed_file is not None:
            changed_files.append(parsed_file)
          current_block = []
        current_block.append(line)

      if current_block:
        parsed_file = self._parse_block(current_block)
        if parsed_file is not None:
          changed_files.append(parsed_file)

      return changed_files

    def _parse_block(self, block_lines: List[str]) -> Optional[ChangedFile]:
      metadata = self._extract_metadata(block_lines)
      added_lines, removed_lines = self._count_hunk_lines(block_lines)
      changed_line_numbers = self._extract_changed_line_numbers(block_lines)

      selected_path = self._select_path(
        change_type=metadata["change_type"],
        old_path=metadata["old_path"],
        new_path=metadata["new_path"],
      )
      if selected_path is None:
        return None

      path = Path(selected_path)
      return ChangedFile(
        path=path,
        change_type=metadata["change_type"],
        language=self._infer_language(path),
        diff_content="".join(block_lines).rstrip("\n"),
        added_lines=added_lines,
        removed_lines=removed_lines,
        changed_line_numbers=changed_line_numbers,
      )

    def _extract_metadata(self, block_lines: List[str]) -> dict[str, Optional[str] | ChangeType]:
      old_path: Optional[str] = None
      new_path: Optional[str] = None
      rename_from: Optional[str] = None
      rename_to: Optional[str] = None
      change_type = ChangeType.MODIFIED

      diff_header_match = re.match(
        r'^diff --git a/(?P<old>.+) b/(?P<new>.+)$',
        block_lines[0].rstrip("\n"),
      )
      if diff_header_match:
        old_path = self._normalize_git_path(diff_header_match.group("old"))
        new_path = self._normalize_git_path(diff_header_match.group("new"))

      for line in block_lines[1:]:
        stripped = line.rstrip("\n")
        change_type, old_path, new_path, rename_from, rename_to = self._update_metadata(
          stripped=stripped,
          change_type=change_type,
          old_path=old_path,
          new_path=new_path,
          rename_from=rename_from,
          rename_to=rename_to,
        )

      return {
        "change_type": change_type,
        "old_path": rename_from or old_path,
        "new_path": rename_to or new_path,
      }

    def _update_metadata(
      self,
      stripped: str,
      change_type: ChangeType,
      old_path: Optional[str],
      new_path: Optional[str],
      rename_from: Optional[str],
      rename_to: Optional[str],
    ) -> tuple[ChangeType, Optional[str], Optional[str], Optional[str], Optional[str]]:
      if stripped.startswith("new file mode "):
        return change_type.ADDED, old_path, new_path, rename_from, rename_to
      if stripped.startswith("deleted file mode "):
        return change_type.DELETED, old_path, new_path, rename_from, rename_to
      if stripped.startswith("rename from "):
        return (
          change_type.RENAMED,
          old_path,
          new_path,
          self._normalize_git_path(stripped.removeprefix("rename from ")),
          rename_to,
        )
      if stripped.startswith("rename to "):
        return (
          change_type,
          old_path,
          new_path,
          rename_from,
          self._normalize_git_path(stripped.removeprefix("rename to ")),
        )
      if stripped.startswith("--- "):
        header_old_path = self._normalize_diff_header_path(stripped.removeprefix("--- "))
        return change_type, header_old_path or old_path, new_path, rename_from, rename_to
      if stripped.startswith("+++ "):
        header_new_path = self._normalize_diff_header_path(stripped.removeprefix("+++ "))
        return change_type, old_path, header_new_path or new_path, rename_from, rename_to
      return change_type, old_path, new_path, rename_from, rename_to

    def _count_hunk_lines(self, block_lines: List[str]) -> tuple[int, int]:
      added_lines = 0
      removed_lines = 0

      for line in block_lines[1:]:
        if line.startswith("+") and not line.startswith("+++"):
          added_lines += 1
        elif line.startswith("-") and not line.startswith("---"):
          removed_lines += 1

      return added_lines, removed_lines

    def _extract_changed_line_numbers(self, block_lines: List[str]) -> tuple[int, ...]:
      changed_line_numbers: list[int] = []
      current_new_line = 0
      seen_hunk = False

      for raw_line in block_lines:
        line = raw_line.rstrip("\n")
        if line.startswith("@@"):
          match = re.search(r"\+(\d+)", line)
          if match:
            current_new_line = int(match.group(1))
            seen_hunk = True
          continue

        if not seen_hunk:
          continue

        if line.startswith("+++") or line.startswith("---"):
          continue

        if line.startswith("+"):
          changed_line_numbers.append(current_new_line)
          current_new_line += 1
          continue

        if line.startswith(" "):
          current_new_line += 1

      return tuple(changed_line_numbers)

    def _select_path(
      self,
      change_type: ChangeType,
      old_path: Optional[str],
      new_path: Optional[str],
    ) -> Optional[str]:
      if change_type == ChangeType.DELETED:
        return old_path or new_path
      return new_path or old_path

    def _normalize_diff_header_path(self, value: str) -> Optional[str]:
      if value == "/dev/null":
        return None
      return self._normalize_git_path(value)

    def _normalize_git_path(self, value: str) -> str:
      normalized = value.strip().strip('"')
      if normalized.startswith("a/") or normalized.startswith("b/"):
        return normalized[2:]
      return normalized

    def _infer_language(self, path: Path) -> Language:
      extension_map = {
        ".py": Language.PYTHON,
        ".cs": Language.CSHARP,
        ".csproj": Language.XML,
        ".sln": Language.CONFIG,
        ".js": Language.JAVASCRIPT,
        ".jsx": Language.JAVASCRIPT,
        ".mjs": Language.JAVASCRIPT,
        ".cjs": Language.JAVASCRIPT,
        ".ts": Language.TYPESCRIPT,
        ".tsx": Language.TYPESCRIPT,
        ".html": Language.HTML,
        ".scss": Language.SCSS,
        ".json": Language.JSON,
        ".xml": Language.XML,
        ".yml": Language.YAML,
        ".yaml": Language.YAML,
        ".toml": Language.TOML,
        ".sql": Language.SQL,
        ".ini": Language.CONFIG,
        ".cfg": Language.CONFIG,
        ".config": Language.CONFIG,
        ".props": Language.XML,
        ".targets": Language.XML,
        ".java": Language.JAVA,
        ".go": Language.GO,
        ".rs": Language.RUST,
      }
      return extension_map.get(path.suffix.lower(), Language.UNKNOWN)
