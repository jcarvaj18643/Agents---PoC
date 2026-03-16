from pathlib import Path

from app.domain.entities.changed_file import ChangedFile
from app.domain.entities.changed_symbol import ChangedSymbol
from app.domain.enums.change_type import ChangeType
from app.domain.enums.language import Language
from app.domain.value_objects.project_profile import ProjectProfile
from app.infrastructure.adapters.validation.profile_impact_target_resolver_adapter import (
    ProfileImpactTargetResolverAdapter,
)


class TestProfileImpactTargetResolverAdapter:
    def test_resolves_python_lint_and_test_targets(self, tmp_path: Path) -> None:
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_service.py").write_text("def test_service():\n    pass\n", encoding="utf-8")
        resolver = ProfileImpactTargetResolverAdapter()
        profile = ProjectProfile("python", "python", None, "pytest", True)
        changed_files = [
            ChangedFile(
                path=Path("service.py"),
                change_type=ChangeType.MODIFIED,
                language=Language.PYTHON,
                diff_content="",
            )
        ]

        resolution = resolver.resolve(str(tmp_path), profile, changed_files)

        assert resolution.working_directory == tmp_path
        assert resolution.lint_targets == ["service.py"]
        assert resolution.test_targets == ["tests/test_service.py"]

    def test_resolves_csharp_owner_projects_and_test_targets(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src" / "Orders"
        src_dir.mkdir(parents=True)
        tests_dir = tmp_path / "tests" / "Orders.Tests"
        tests_dir.mkdir(parents=True)
        (src_dir / "Orders.csproj").write_text("<Project />", encoding="utf-8")
        (tests_dir / "Orders.Tests.csproj").write_text("<Project />", encoding="utf-8")
        resolver = ProfileImpactTargetResolverAdapter()
        profile = ProjectProfile("csharp-aspnetcore", "csharp", "aspnetcore", None, True)
        changed_files = [
            ChangedFile(
                path=Path("src/Orders/OrderService.cs"),
                change_type=ChangeType.MODIFIED,
                language=Language.CSHARP,
                diff_content="",
            )
        ]

        resolution = resolver.resolve(str(src_dir.parent), profile, changed_files)

        assert resolution.working_directory == tmp_path
        assert resolution.owner_projects == ["src/Orders/Orders.csproj"]
        assert resolution.test_targets == ["tests/Orders.Tests/Orders.Tests.csproj"]
        assert resolution.lint_targets == []

    def test_resolves_angular_module_owners_and_spec_targets(self, tmp_path: Path) -> None:
        component_dir = tmp_path / "src" / "app"
        component_dir.mkdir(parents=True)
        (component_dir / "users.component.ts").write_text("export class UsersComponent {}", encoding="utf-8")
        (component_dir / "users.component.html").write_text("<div></div>", encoding="utf-8")
        (component_dir / "users.component.scss").write_text(".users {}", encoding="utf-8")
        (component_dir / "users.component.spec.ts").write_text("describe('users', () => {});", encoding="utf-8")
        resolver = ProfileImpactTargetResolverAdapter()
        profile = ProjectProfile("typescript-angular", "typescript", "angular", "karma", True)
        changed_files = [
            ChangedFile(
                path=Path("src/app/users.component.ts"),
                change_type=ChangeType.MODIFIED,
                language=Language.TYPESCRIPT,
                diff_content="",
                impacted_symbol=ChangedSymbol(
                    name="UsersComponent.render",
                    symbol_type="method",
                    change_type=ChangeType.MODIFIED,
                    file_path="src/app/users.component.ts",
                    start_line=1,
                    end_line=5,
                ),
            )
        ]

        resolution = resolver.resolve(str(tmp_path), profile, changed_files)

        assert resolution.working_directory == tmp_path
        assert resolution.module_owners == ["src/app/users.component"]
        assert resolution.lint_targets == [
            "src/app/users.component.html",
            "src/app/users.component.scss",
            "src/app/users.component.ts",
        ]
        assert resolution.test_targets == ["src/app/users.component.spec.ts"]