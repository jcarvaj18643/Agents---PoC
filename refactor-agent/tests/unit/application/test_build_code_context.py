"""Unit tests for BuildCodeContextUseCase."""

from pathlib import Path

from app.application.use_cases.build_code_context import BuildCodeContextUseCase
from app.domain.entities.changed_file import ChangedFile
from app.domain.entities.code_scope import CodeScope
from app.domain.enums.change_type import ChangeType
from app.domain.enums.language import Language
from app.infrastructure.adapters.filesystem.filesystem_adapter import FileSystemAdapter
from app.infrastructure.adapters.policy_loader.repository_prompt_guidance_loader_adapter import (
    RepositoryPromptGuidanceLoaderAdapter,
)
from app.infrastructure.adapters.parser.heuristic_symbol_context_resolver_adapter import (
    HeuristicSymbolContextResolverAdapter,
)


class TestBuildCodeContextUseCase:
    def test_enriches_changed_file_with_diff_scoped_context_snapshot(self, tmp_path: Path) -> None:
        repo_file = tmp_path / "app.py"
        repo_file.write_text(
            "def run() -> int:\n    old_value = 1\n    return old_value\n",
            encoding="utf-8",
        )

        scope = CodeScope(
            changed_files=[
                ChangedFile(
                    path=Path("app.py"),
                    change_type=ChangeType.MODIFIED,
                    language=Language.PYTHON,
                    diff_content=(
                        "diff --git a/app.py b/app.py\n"
                        "@@ -1,3 +1,3 @@\n"
                        " def run() -> int:\n"
                        "-    old_value = 1\n"
                        "+    new_value = 2\n"
                        "+    return new_value\n"
                    ),
                )
            ]
        )

        files = BuildCodeContextUseCase(FileSystemAdapter()).execute(scope, str(tmp_path))

        assert len(files) == 1
        assert "def run() -> int:" in files[0].context_snapshot
        assert "new_value = 2" in files[0].context_snapshot
        assert "old_value = 1" not in files[0].context_snapshot
        assert "old_value = 1" in files[0].full_file_context

    def test_keeps_full_file_context_alongside_changed_hunk_context(self, tmp_path: Path) -> None:
        repo_file = tmp_path / "service.py"
        repo_file.write_text(
            "def helper(value: int) -> int:\n    return value * 2\n\n"
            "def run() -> int:\n    result = helper(3)\n    return result\n",
            encoding="utf-8",
        )

        scope = CodeScope(
            changed_files=[
                ChangedFile(
                    path=Path("service.py"),
                    change_type=ChangeType.MODIFIED,
                    language=Language.PYTHON,
                    diff_content=(
                        "diff --git a/service.py b/service.py\n"
                        "@@ -3,2 +3,3 @@\n"
                        " def run() -> int:\n"
                        "+    result = helper(3)\n"
                        "     return result\n"
                    ),
                )
            ]
        )

        files = BuildCodeContextUseCase(FileSystemAdapter()).execute(scope, str(tmp_path))

        assert "result = helper(3)" in files[0].changed_hunk_context
        assert "def helper(value: int) -> int:" in files[0].full_file_context

    def test_falls_back_to_file_contents_when_diff_has_no_hunk_content(self, tmp_path: Path) -> None:
        repo_file = tmp_path / "added.py"
        repo_file.write_text("def created() -> int:\n    return 3\n", encoding="utf-8")

        scope = CodeScope(
            changed_files=[
                ChangedFile(
                    path=Path("added.py"),
                    change_type=ChangeType.ADDED,
                    language=Language.PYTHON,
                    diff_content="diff --git a/added.py b/added.py",
                )
            ]
        )

        files = BuildCodeContextUseCase(FileSystemAdapter()).execute(scope, str(tmp_path))

        assert "def created() -> int:" in files[0].context_snapshot
        assert "def created() -> int:" in files[0].full_file_context

    def test_leaves_context_empty_when_file_does_not_exist(self, tmp_path: Path) -> None:
        scope = CodeScope(
            changed_files=[
                ChangedFile(
                    path=Path("deleted.py"),
                    change_type=ChangeType.DELETED,
                    language=Language.PYTHON,
                    diff_content="diff --git a/deleted.py b/deleted.py",
                )
            ]
        )

        files = BuildCodeContextUseCase(FileSystemAdapter()).execute(scope, str(tmp_path))

        assert files[0].context_snapshot == ""

    def test_resolves_impacted_python_symbol_context(self, tmp_path: Path) -> None:
        repo_file = tmp_path / "service.py"
        repo_file.write_text(
            "class Service:\n"
            "    def helper(self) -> int:\n"
            "        return 1\n\n"
            "    def run(self) -> int:\n"
            "        value = self.helper()\n"
            "        return value\n",
            encoding="utf-8",
        )

        scope = CodeScope(
            changed_files=[
                ChangedFile(
                    path=Path("service.py"),
                    change_type=ChangeType.MODIFIED,
                    language=Language.PYTHON,
                    diff_content=(
                        "diff --git a/service.py b/service.py\n"
                        "@@ -5,2 +5,3 @@\n"
                        "     def run(self) -> int:\n"
                        "+        value = self.helper()\n"
                        "         return value\n"
                    ),
                )
            ]
        )

        files = BuildCodeContextUseCase(
            FileSystemAdapter(),
            symbol_context_resolver=HeuristicSymbolContextResolverAdapter(),
        ).execute(scope, str(tmp_path))

        assert files[0].impacted_symbol is not None
        assert files[0].impacted_symbol.name == "run"
        assert files[0].symbol_context.startswith("def run")

    def test_resolves_impacted_csharp_method_with_class_qualification(self, tmp_path: Path) -> None:
        repo_file = tmp_path / "OrderService.cs"
        repo_file.write_text(
            "namespace Demo;\n\n"
            "public class OrderService\n"
            "{\n"
            "    public async Task<int> LoadAsync()\n"
            "    {\n"
            "        return 1;\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        scope = CodeScope(
            changed_files=[
                ChangedFile(
                    path=Path("OrderService.cs"),
                    change_type=ChangeType.MODIFIED,
                    language=Language.CSHARP,
                    diff_content=(
                        "diff --git a/OrderService.cs b/OrderService.cs\n"
                        "@@ -5,2 +5,3 @@\n"
                        "     {\n"
                        "+        return 2;\n"
                        "     }\n"
                    ),
                )
            ]
        )

        files = BuildCodeContextUseCase(
            FileSystemAdapter(),
            symbol_context_resolver=HeuristicSymbolContextResolverAdapter(),
        ).execute(scope, str(tmp_path))

        assert files[0].impacted_symbol is not None
        assert files[0].impacted_symbol.name == "OrderService.LoadAsync"
        assert files[0].impacted_symbol.symbol_type == "method"
        assert "LoadAsync" in files[0].symbol_context

    def test_resolves_impacted_angular_class_from_decorator_block(self, tmp_path: Path) -> None:
        repo_file = tmp_path / "users.component.ts"
        repo_file.write_text(
            "@Component({\n"
            "  selector: 'app-users',\n"
            "  templateUrl: './users.component.html',\n"
            "})\n"
            "export class UsersComponent {\n"
            "  loadUsers(): void {\n"
            "    console.log('load');\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        scope = CodeScope(
            changed_files=[
                ChangedFile(
                    path=Path("users.component.ts"),
                    change_type=ChangeType.MODIFIED,
                    language=Language.TYPESCRIPT,
                    diff_content=(
                        "diff --git a/users.component.ts b/users.component.ts\n"
                        "@@ -1,3 +1,4 @@\n"
                        " @Component({\n"
                        "+  standalone: true,\n"
                        "   selector: 'app-users',\n"
                    ),
                )
            ]
        )

        files = BuildCodeContextUseCase(
            FileSystemAdapter(),
            symbol_context_resolver=HeuristicSymbolContextResolverAdapter(),
        ).execute(scope, str(tmp_path))

        assert files[0].impacted_symbol is not None
        assert files[0].impacted_symbol.name == "UsersComponent"
        assert files[0].impacted_symbol.symbol_type == "class"
        assert files[0].symbol_context.startswith("@Component")

    def test_prefers_actual_added_line_numbers_when_resolving_symbol(self, tmp_path: Path) -> None:
        repo_file = tmp_path / "service.py"
        repo_file.write_text(
            "def first() -> int:\n"
            "    return 1\n\n"
            "def second() -> int:\n"
            "    return 2\n",
            encoding="utf-8",
        )

        scope = CodeScope(
            changed_files=[
                ChangedFile(
                    path=Path("service.py"),
                    change_type=ChangeType.MODIFIED,
                    language=Language.PYTHON,
                    diff_content=(
                        "diff --git a/service.py b/service.py\n"
                        "@@ -1,4 +1,5 @@\n"
                        " def first() -> int:\n"
                        "     return 1\n"
                        "\n"
                        " def second() -> int:\n"
                        "+    value = 3\n"
                        "     return 2\n"
                    ),
                    changed_line_numbers=(5,),
                )
            ]
        )

        files = BuildCodeContextUseCase(
            FileSystemAdapter(),
            symbol_context_resolver=HeuristicSymbolContextResolverAdapter(),
        ).execute(scope, str(tmp_path))

        assert files[0].impacted_symbol is not None
        assert files[0].impacted_symbol.name == "second"
        assert files[0].changed_line_numbers == (5,)

    def test_attaches_repository_prompt_guidance_when_configuration_file_exists(self, tmp_path: Path) -> None:
        (tmp_path / "repository-guidance.yaml").write_text(
            "repository:\n"
            "  name: rag_system\n"
            "  framework: .NET 8\n"
            "  architecture: Hexagonal\n"
            "layers:\n"
            "  - name: persistence\n"
            "    path: src/Persistence\n"
            "    responsibility: adapters and repositories\n",
            encoding="utf-8",
        )
        repo_file = tmp_path / "service.py"
        repo_file.write_text("def run() -> int:\n    return 1\n", encoding="utf-8")
        scope = CodeScope(
            changed_files=[
                ChangedFile(
                    path=Path("service.py"),
                    change_type=ChangeType.MODIFIED,
                    language=Language.PYTHON,
                    diff_content="diff --git a/service.py b/service.py",
                )
            ]
        )

        files = BuildCodeContextUseCase(
            FileSystemAdapter(),
            repository_prompt_guidance_loader=RepositoryPromptGuidanceLoaderAdapter(),
        ).execute(scope, str(tmp_path), "python")

        assert "Repository name: rag_system" in files[0].repository_guidance
        assert "Framework or platform: .NET 8" in files[0].repository_guidance
        assert "persistence: path=src/Persistence; responsibility=adapters and repositories" in files[0].repository_guidance