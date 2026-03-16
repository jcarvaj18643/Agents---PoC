"""Unit tests for YamlPolicyLoaderAdapter."""

from pathlib import Path

from app.infrastructure.adapters.policy_loader.yaml_policy_loader_adapter import (
    YamlPolicyLoaderAdapter,
)


class TestYamlPolicyLoaderAdapter:
    def test_loads_profile_policies(self, tmp_path: Path) -> None:
        (tmp_path / "python.yaml").write_text(
            "version: '1.0.0'\npolicies:\n  - id: p1\n    name: Policy One\n    description: First policy\n    applies_to: ['*.py']\n    rules:\n      - type: documentation\n        instruction: Add docstrings\n",
            encoding="utf-8",
        )

        policies = YamlPolicyLoaderAdapter(tmp_path).load_policies("python")

        assert len(policies) == 1
        assert policies[0].id == "p1"
        assert policies[0].applies_to == ("*.py",)

    def test_falls_back_to_language_and_default(self, tmp_path: Path) -> None:
        (tmp_path / "python.yaml").write_text(
            "policies:\n  - id: python-base\n    name: Python Base\n    description: Base python policy\n    applies_to: ['*.py']\n    rules:\n      - type: scope\n        instruction: Stay in scope\n",
            encoding="utf-8",
        )
        (tmp_path / "default.yaml").write_text(
            "policies:\n  - id: default-base\n    name: Default Base\n    description: Default policy\n    applies_to: ['*']\n    rules:\n      - type: reporting\n        instruction: Report scope\n",
            encoding="utf-8",
        )

        policies = YamlPolicyLoaderAdapter(tmp_path).load_policies("python-fastapi")

        assert {policy.id for policy in policies} == {"python-base", "default-base"}

    def test_loads_framework_specific_policy_file(self, tmp_path: Path) -> None:
        (tmp_path / "typescript-angular.yaml").write_text(
            "policies:\n  - id: angular-base\n    name: Angular Base\n    description: Angular policy\n    applies_to: ['*.ts', '*.html']\n    rules:\n      - type: scope\n        instruction: Stay in scope\n",
            encoding="utf-8",
        )
        (tmp_path / "default.yaml").write_text(
            "policies:\n  - id: default-base\n    name: Default Base\n    description: Default policy\n    applies_to: ['*']\n    rules:\n      - type: reporting\n        instruction: Report scope\n",
            encoding="utf-8",
        )

        policies = YamlPolicyLoaderAdapter(tmp_path).load_policies("typescript-angular")

        assert {policy.id for policy in policies} == {"angular-base", "default-base"}