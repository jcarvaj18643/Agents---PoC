"""Unit tests for the CodeScope domain entity."""

from pathlib import Path

import pytest

from app.domain.entities.changed_file import ChangedFile
from app.domain.entities.code_scope import CodeScope
from app.domain.enums.change_type import ChangeType
from app.domain.enums.language import Language


def _make_file(
    path: str = "src/foo.py",
    language: Language = Language.PYTHON,
    change_type: ChangeType = ChangeType.MODIFIED,
) -> ChangedFile:
    return ChangedFile(
        path=Path(path),
        change_type=change_type,
        language=language,
        diff_content="",
    )


class TestCodeScopeProperties:
    def test_is_empty_when_no_files(self) -> None:
        scope = CodeScope()
        assert scope.is_empty is True

    def test_not_empty_when_files_present(self) -> None:
        scope = CodeScope(changed_files=[_make_file()])
        assert scope.is_empty is False

    def test_total_files_reflects_count(self) -> None:
        scope = CodeScope(changed_files=[_make_file(), _make_file("src/bar.py")])
        assert scope.total_files == 2

    def test_total_files_zero_for_empty_scope(self) -> None:
        assert CodeScope().total_files == 0


class TestCodeScopeRefs:
    def test_base_and_head_refs_are_stored(self) -> None:
        scope = CodeScope(base_ref="main", head_ref="feature/my-branch")
        assert scope.base_ref == "main"
        assert scope.head_ref == "feature/my-branch"

    def test_default_refs_are_empty_strings(self) -> None:
        scope = CodeScope()
        assert scope.base_ref == ""
        assert scope.head_ref == ""
