"""Unit tests for DiffParser."""

from app.domain.enums.change_type import ChangeType
from app.domain.enums.language import Language
from app.infrastructure.parsers.diff_parser import DiffParser
from tests.fixtures.sample_diff import (
    ANGULAR_CONFIG_DIFF,
    ANGULAR_STYLES_DIFF,
    ANGULAR_TEMPLATE_DIFF,
    ANGULAR_TYPESCRIPT_DIFF,
    CSHARP_DIFF,
    CSHARP_PROJECT_DIFF,
    DELETED_FILE_DIFF,
    EMPTY_DIFF,
    MULTI_FILE_DIFF,
    RENAMED_FILE_DIFF,
    SAMPLE_UNIFIED_DIFF,
)


class TestDiffParser:
    def test_returns_empty_list_for_empty_diff(self) -> None:
        parser = DiffParser()

        assert parser.parse(EMPTY_DIFF) == []

    def test_parses_modified_python_file(self) -> None:
        parser = DiffParser()

        files = parser.parse(SAMPLE_UNIFIED_DIFF)

        assert len(files) == 1
        assert files[0].path.as_posix() == "app/service.py"
        assert files[0].change_type == ChangeType.MODIFIED
        assert files[0].language == Language.PYTHON
        assert files[0].added_lines == 4
        assert files[0].removed_lines == 2

    def test_parses_multiple_files(self) -> None:
        parser = DiffParser()

        files = parser.parse(MULTI_FILE_DIFF)

        assert len(files) == 2
        assert files[0].path.as_posix() == "app/models.py"
        assert files[0].change_type == ChangeType.ADDED
        assert files[1].path.as_posix() == "app/service.py"
        assert files[1].change_type == ChangeType.MODIFIED

    def test_parses_deleted_file(self) -> None:
        parser = DiffParser()

        files = parser.parse(DELETED_FILE_DIFF)

        assert len(files) == 1
        assert files[0].path.as_posix() == "app/legacy.py"
        assert files[0].change_type == ChangeType.DELETED
        assert files[0].removed_lines == 3

    def test_parses_renamed_file(self) -> None:
        parser = DiffParser()

        files = parser.parse(RENAMED_FILE_DIFF)

        assert len(files) == 1
        assert files[0].path.as_posix() == "app/new_name.py"
        assert files[0].change_type == ChangeType.RENAMED

    def test_parses_csharp_file(self) -> None:
        parser = DiffParser()

        files = parser.parse(CSHARP_DIFF)

        assert len(files) == 1
        assert files[0].path.as_posix() == "src/App/Program.cs"
        assert files[0].language == Language.CSHARP

    def test_parses_angular_typescript_file(self) -> None:
        parser = DiffParser()

        files = parser.parse(ANGULAR_TYPESCRIPT_DIFF)

        assert len(files) == 1
        assert files[0].path.as_posix() == "src/app/app.component.ts"
        assert files[0].language == Language.TYPESCRIPT

    def test_parses_angular_template_file(self) -> None:
        parser = DiffParser()

        files = parser.parse(ANGULAR_TEMPLATE_DIFF)

        assert len(files) == 1
        assert files[0].path.as_posix() == "src/app/app.component.html"
        assert files[0].language == Language.HTML

    def test_parses_angular_stylesheet_file(self) -> None:
        parser = DiffParser()

        files = parser.parse(ANGULAR_STYLES_DIFF)

        assert len(files) == 1
        assert files[0].path.as_posix() == "src/app/app.component.scss"
        assert files[0].language == Language.SCSS

    def test_parses_angular_config_file(self) -> None:
        parser = DiffParser()

        files = parser.parse(ANGULAR_CONFIG_DIFF)

        assert len(files) == 1
        assert files[0].path.as_posix() == "angular.json"
        assert files[0].language == Language.JSON

    def test_parses_csharp_project_file(self) -> None:
        parser = DiffParser()

        files = parser.parse(CSHARP_PROJECT_DIFF)

        assert len(files) == 1
        assert files[0].path.as_posix() == "src/App/App.csproj"
        assert files[0].language == Language.XML