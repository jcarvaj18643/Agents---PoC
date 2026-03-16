"""Unit tests for ProjectStructureReaderAdapter."""

from pathlib import Path

from app.infrastructure.adapters.filesystem.project_structure_reader_adapter import (
    ProjectStructureReaderAdapter,
)


class TestProjectStructureReaderAdapter:
    def test_detects_python_profile_with_pytest_and_type_hints(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            "[project]\nname = 'sample'\n[tool.pytest.ini_options]\naddopts='-q'\n",
            encoding="utf-8",
        )
        (tmp_path / "tests").mkdir()
        (tmp_path / "app.py").write_text(
            "def run(value: int) -> int:\n    return value\n",
            encoding="utf-8",
        )

        profile = ProjectStructureReaderAdapter().read_structure(str(tmp_path))

        assert profile.name == "python"
        assert profile.language == "python"
        assert profile.test_framework == "pytest"
        assert profile.has_type_hints is True

    def test_detects_python_fastapi_profile(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("fastapi==0.115.0\npytest==8.0.0\n", encoding="utf-8")

        profile = ProjectStructureReaderAdapter().read_structure(str(tmp_path))

        assert profile.name == "python-fastapi"
        assert profile.framework == "fastapi"

    def test_detects_csharp_profile(self, tmp_path: Path) -> None:
        (tmp_path / "Sample.sln").write_text("Microsoft Visual Studio Solution File", encoding="utf-8")
        (tmp_path / "App.csproj").write_text(
            "<Project><ItemGroup><PackageReference Include=\"xunit\" Version=\"2.0.0\" /></ItemGroup></Project>",
            encoding="utf-8",
        )
        (tmp_path / "Program.cs").write_text(
            "var builder = WebApplication.CreateBuilder(args);\n",
            encoding="utf-8",
        )

        profile = ProjectStructureReaderAdapter().read_structure(str(tmp_path))

        assert profile.language == "csharp"
        assert profile.name == "csharp-aspnetcore"
        assert profile.framework == "aspnetcore"
        assert profile.test_framework == "xunit"
        assert profile.has_type_hints is True

    def test_detects_angular_typescript_profile(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(
            '{"dependencies": {"@angular/core": "18.0.0"}, "devDependencies": {"jest": "29.0.0"}}',
            encoding="utf-8",
        )
        (tmp_path / "tsconfig.json").write_text("{}", encoding="utf-8")
        (tmp_path / "angular.json").write_text('{"projects": {"web": {}}}', encoding="utf-8")

        profile = ProjectStructureReaderAdapter().read_structure(str(tmp_path))

        assert profile.language == "typescript"
        assert profile.name == "typescript-angular"
        assert profile.framework == "angular"
        assert profile.test_framework == "jest"
        assert profile.has_type_hints is True

    def test_ignores_dependency_sources_when_detecting_angular_profile(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(
            '{"dependencies": {"@angular/core": "18.0.0"}, "devDependencies": {"karma": "6.0.0"}}',
            encoding="utf-8",
        )
        (tmp_path / "tsconfig.json").write_text("{}", encoding="utf-8")
        (tmp_path / "angular.json").write_text('{"projects": {"web": {}}}', encoding="utf-8")
        node_module_dir = tmp_path / "node_modules" / "some-package"
        node_module_dir.mkdir(parents=True)
        (node_module_dir / "Program.cs").write_text("class Program {}\n", encoding="utf-8")

        profile = ProjectStructureReaderAdapter().read_structure(str(tmp_path))

        assert profile.language == "typescript"
        assert profile.name == "typescript-angular"