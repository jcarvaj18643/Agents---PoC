from pathlib import Path

from app.application.use_cases.filter_scope_by_profile import FilterScopeByProfileUseCase
from app.domain.entities.changed_file import ChangedFile
from app.domain.entities.code_scope import CodeScope
from app.domain.enums.change_type import ChangeType
from app.domain.enums.language import Language
from app.domain.value_objects.project_profile import ProjectProfile


class TestFilterScopeByProfileUseCase:
    def test_keeps_only_python_files_for_python_profile(self) -> None:
        scope = CodeScope(
            changed_files=[
                ChangedFile(Path("app/service.py"), ChangeType.MODIFIED, Language.PYTHON, ""),
                ChangedFile(Path("pyproject.toml"), ChangeType.MODIFIED, Language.TOML, ""),
                ChangedFile(Path("db/migration.sql"), ChangeType.MODIFIED, Language.SQL, ""),
                ChangedFile(Path("README.md"), ChangeType.MODIFIED, Language.UNKNOWN, ""),
            ]
        )
        profile = ProjectProfile(
            name="python",
            language="python",
            framework=None,
            test_framework="pytest",
            has_type_hints=True,
        )

        filtered_scope = FilterScopeByProfileUseCase().execute(scope, profile)

        assert [file.path.as_posix() for file in filtered_scope.changed_files] == [
            "app/service.py",
            "pyproject.toml",
            "db/migration.sql",
        ]

    def test_keeps_ts_html_and_scss_for_angular_profile(self) -> None:
        scope = CodeScope(
            changed_files=[
                ChangedFile(Path("src/app/app.component.ts"), ChangeType.MODIFIED, Language.TYPESCRIPT, ""),
                ChangedFile(Path("src/app/app.component.html"), ChangeType.MODIFIED, Language.HTML, ""),
                ChangedFile(Path("src/app/app.component.scss"), ChangeType.MODIFIED, Language.SCSS, ""),
                ChangedFile(Path("angular.json"), ChangeType.MODIFIED, Language.JSON, ""),
                ChangedFile(Path("package.json"), ChangeType.MODIFIED, Language.JSON, ""),
                ChangedFile(Path("tsconfig.app.json"), ChangeType.MODIFIED, Language.JSON, ""),
                ChangedFile(Path("karma.conf.js"), ChangeType.MODIFIED, Language.JAVASCRIPT, ""),
                ChangedFile(Path("docs/frontend-api-guide.md"), ChangeType.MODIFIED, Language.UNKNOWN, ""),
                ChangedFile(Path("docs/mock.json"), ChangeType.MODIFIED, Language.JSON, ""),
            ]
        )
        profile = ProjectProfile(
            name="typescript-angular",
            language="typescript",
            framework="angular",
            test_framework="karma",
            has_type_hints=True,
        )

        filtered_scope = FilterScopeByProfileUseCase().execute(scope, profile)

        assert [file.path.as_posix() for file in filtered_scope.changed_files] == [
            "src/app/app.component.ts",
            "src/app/app.component.html",
            "src/app/app.component.scss",
            "angular.json",
            "package.json",
            "tsconfig.app.json",
            "karma.conf.js",
        ]

    def test_keeps_csharp_project_and_runtime_config_files(self) -> None:
        scope = CodeScope(
            changed_files=[
                ChangedFile(Path("src/App/Program.cs"), ChangeType.MODIFIED, Language.CSHARP, ""),
                ChangedFile(Path("src/App/App.csproj"), ChangeType.MODIFIED, Language.XML, ""),
                ChangedFile(Path("src/App/appsettings.Development.json"), ChangeType.MODIFIED, Language.JSON, ""),
                ChangedFile(Path("src/App/web.config"), ChangeType.MODIFIED, Language.CONFIG, ""),
                ChangedFile(Path("database/migrations/001_init.sql"), ChangeType.MODIFIED, Language.SQL, ""),
                ChangedFile(Path("docs/contract.json"), ChangeType.MODIFIED, Language.JSON, ""),
            ]
        )
        profile = ProjectProfile(
            name="csharp",
            language="csharp",
            framework="aspnetcore",
            test_framework="xunit",
            has_type_hints=True,
        )

        filtered_scope = FilterScopeByProfileUseCase().execute(scope, profile)

        assert [file.path.as_posix() for file in filtered_scope.changed_files] == [
            "src/App/Program.cs",
            "src/App/App.csproj",
            "src/App/appsettings.Development.json",
            "src/App/web.config",
            "database/migrations/001_init.sql",
        ]

    def test_returns_empty_scope_when_no_files_match_profile_language(self) -> None:
        scope = CodeScope(
            changed_files=[
                ChangedFile(Path("README.md"), ChangeType.MODIFIED, Language.UNKNOWN, ""),
                ChangedFile(Path("docs/guide.md"), ChangeType.MODIFIED, Language.UNKNOWN, ""),
            ]
        )
        profile = ProjectProfile(
            name="csharp",
            language="csharp",
            framework=None,
            test_framework="xunit",
            has_type_hints=True,
        )

        filtered_scope = FilterScopeByProfileUseCase().execute(scope, profile)

        assert filtered_scope.is_empty is True