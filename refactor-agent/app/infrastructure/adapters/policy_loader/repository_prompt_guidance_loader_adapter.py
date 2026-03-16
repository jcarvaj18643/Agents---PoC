import json
from pathlib import Path
from typing import Any

import yaml

from app.application.ports.outbound.repository_prompt_guidance_port import (
    RepositoryPromptGuidancePort,
)
from app.domain.value_objects.repository_prompt_guidance import RepositoryPromptGuidance
from app.infrastructure.logging.console_logger import get_logger

logger = get_logger(__name__)


class RepositoryPromptGuidanceLoaderAdapter(RepositoryPromptGuidancePort):
    """Loads repository-specific LLM prompt guidance from YAML or JSON files."""

    def __init__(self, base_name: str = "repository-guidance") -> None:
        self._base_name = base_name

    def load(self, repo_path: str, profile_name: str | None = None) -> RepositoryPromptGuidance | None:
        root = Path(repo_path)
        for candidate in self._candidate_paths(root, profile_name):
            if not candidate.exists():
                continue
            logger.info("Loading repository prompt guidance from %s", candidate)
            raw = self._load_structured_file(candidate)
            return self._parse_guidance(raw, candidate)
        logger.info("No repository prompt guidance file found under %s", root)
        return None

    def _candidate_paths(self, root: Path, profile_name: str | None) -> list[Path]:
        names: list[str] = []
        if profile_name:
            names.append(f"{self._base_name}.{profile_name}")
            if "-" in profile_name:
                names.append(f"{self._base_name}.{profile_name.split('-', maxsplit=1)[0]}")
        names.append(self._base_name)

        unique_names: list[str] = []
        for name in names:
            if name not in unique_names:
                unique_names.append(name)

        candidates: list[Path] = []
        for directory in (root / "prompt-guidance", root, root / ".github"):
            for name in unique_names:
                candidates.extend(
                    [
                        directory / f"{name}.yaml",
                        directory / f"{name}.yml",
                        directory / f"{name}.json",
                    ]
                )
        return candidates

    def _load_structured_file(self, path: Path) -> dict[str, Any]:
        content = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".json":
            raw = json.loads(content)
        else:
            raw = yaml.safe_load(content)
        if not isinstance(raw, dict):
            raise ValueError(f"Invalid repository guidance schema in {path}: expected mapping")
        return raw

    def _parse_guidance(self, raw: dict[str, Any], source_path: Path) -> RepositoryPromptGuidance:
        repository = raw.get("repository") if isinstance(raw.get("repository"), dict) else {}
        layers = raw.get("layers") if isinstance(raw.get("layers"), list) else []
        return RepositoryPromptGuidance(
            source_path=str(source_path),
            repository_name=self._read_optional_string(repository, "name"),
            framework=self._read_optional_string(repository, "framework"),
            architecture=self._read_optional_string(repository, "architecture"),
            summary=self._read_optional_string(repository, "summary"),
            design_principles=self._read_string_list(raw.get("design_principles")),
            layer_conventions=self._format_layers(layers),
            refactor_guardrails=self._read_string_list(raw.get("refactor_guardrails")),
            naming_conventions=self._read_string_list(raw.get("naming_conventions")),
            additional_instructions=self._read_string_list(raw.get("additional_instructions")),
        )

    def _read_optional_string(self, raw: dict[str, Any], key: str) -> str | None:
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    def _read_string_list(self, raw: Any) -> tuple[str, ...]:
        if not isinstance(raw, list):
            return ()
        return tuple(item.strip() for item in raw if isinstance(item, str) and item.strip())

    def _format_layers(self, layers: list[Any]) -> tuple[str, ...]:
        formatted: list[str] = []
        for item in layers:
            if not isinstance(item, dict):
                continue
            name = self._read_optional_string(item, "name")
            path = self._read_optional_string(item, "path")
            responsibility = self._read_optional_string(item, "responsibility")
            allowed = ", ".join(self._read_string_list(item.get("allowed_dependencies")))
            forbidden = ", ".join(self._read_string_list(item.get("forbidden_dependencies")))

            details: list[str] = []
            if path:
                details.append(f"path={path}")
            if responsibility:
                details.append(f"responsibility={responsibility}")
            if allowed:
                details.append(f"allowed={allowed}")
            if forbidden:
                details.append(f"forbidden={forbidden}")

            if name and details:
                formatted.append(f"{name}: {'; '.join(details)}")
            elif name:
                formatted.append(name)
        return tuple(formatted)