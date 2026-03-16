from pathlib import Path

from app.infrastructure.adapters.policy_loader.repository_prompt_guidance_loader_adapter import (
    RepositoryPromptGuidanceLoaderAdapter,
)


class TestRepositoryPromptGuidanceLoaderAdapter:
    def test_loads_yaml_repository_guidance(self, tmp_path: Path) -> None:
        guidance_dir = tmp_path / "prompt-guidance"
        guidance_dir.mkdir()
        (guidance_dir / "repository-guidance.yaml").write_text(
            "repository:\n"
            "  name: rag_system\n"
            "  framework: .NET 8\n"
            "  architecture: Hexagonal\n"
            "design_principles:\n"
            "  - Apply SOLID\n"
            "layers:\n"
            "  - name: api\n"
            "    path: src/Api\n"
            "    responsibility: HTTP endpoints\n",
            encoding="utf-8",
        )

        guidance = RepositoryPromptGuidanceLoaderAdapter().load(str(tmp_path), "csharp")

        assert guidance is not None
        assert guidance.repository_name == "rag_system"
        assert guidance.framework == ".NET 8"
        assert guidance.architecture == "Hexagonal"
        assert guidance.design_principles == ("Apply SOLID",)
        assert guidance.layer_conventions == ("api: path=src/Api; responsibility=HTTP endpoints",)

    def test_prefers_prompt_guidance_directory_over_root_file(self, tmp_path: Path) -> None:
        (tmp_path / "repository-guidance.yaml").write_text(
            "repository:\n  name: root-guidance\n",
            encoding="utf-8",
        )
        guidance_dir = tmp_path / "prompt-guidance"
        guidance_dir.mkdir()
        (guidance_dir / "repository-guidance.yaml").write_text(
            "repository:\n  name: folder-guidance\n",
            encoding="utf-8",
        )

        guidance = RepositoryPromptGuidanceLoaderAdapter().load(str(tmp_path), "python")

        assert guidance is not None
        assert guidance.repository_name == "folder-guidance"

    def test_loads_profile_specific_json_before_default(self, tmp_path: Path) -> None:
        (tmp_path / "repository-guidance.json").write_text(
            '{"repository":{"name":"default-repo","framework":"generic"}}',
            encoding="utf-8",
        )
        (tmp_path / "repository-guidance.python.json").write_text(
            '{"repository":{"name":"python-repo","framework":"FastAPI"}}',
            encoding="utf-8",
        )

        guidance = RepositoryPromptGuidanceLoaderAdapter().load(str(tmp_path), "python")

        assert guidance is not None
        assert guidance.repository_name == "python-repo"
        assert guidance.framework == "FastAPI"