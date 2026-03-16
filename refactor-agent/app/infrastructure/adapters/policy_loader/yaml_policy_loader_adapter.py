from pathlib import Path
from typing import Any, List

import yaml

from app.application.ports.outbound.policy_repository_port import PolicyRepositoryPort
from app.domain.value_objects.engineering_policy import EngineeringPolicy
from app.infrastructure.logging.console_logger import get_logger

logger = get_logger(__name__)


class YamlPolicyLoaderAdapter(PolicyRepositoryPort):
    """Adapter: loads engineering policies from YAML files in a policies directory.

    File naming convention (to be formalised):
        policies/<profile_name>.yaml
        policies/<profile_name>/*.yaml  (one file per rule group)

    TODO: implement recursive directory scan, schema validation, and caching.
    """

    def __init__(self, policies_dir: Path) -> None:
        self._policies_dir = policies_dir

    def load_policies(self, profile_name: str) -> List[EngineeringPolicy]:
        logger.info("Loading policies for profile '%s' from %s", profile_name, self._policies_dir)

        loaded_policies: List[EngineeringPolicy] = []
        for candidate in self._candidate_paths(profile_name):
            if not candidate.exists():
                continue
            loaded_policies.extend(self._load_from_path(candidate))

        if not loaded_policies:
            logger.warning(
                "No policy files found for profile '%s' in %s",
                profile_name,
                self._policies_dir,
            )
        return loaded_policies

    def _candidate_paths(self, profile_name: str) -> list[Path]:
        names = [profile_name]
        if "-" in profile_name:
            names.append(profile_name.split("-", maxsplit=1)[0])
        if "default" not in names:
            names.append("default")

        candidates: list[Path] = []
        for name in names:
            candidates.extend(
                [
                    self._policies_dir / f"{name}.yaml",
                    self._policies_dir / f"{name}.yml",
                    self._policies_dir / name,
                ]
            )
        return candidates

    def _load_from_path(self, path: Path) -> List[EngineeringPolicy]:
        if path.is_dir():
            policies: List[EngineeringPolicy] = []
            for file_path in sorted(path.glob("*.y*ml")):
                policies.extend(self._load_file(file_path))
            return policies
        return self._load_file(path)

    def _load_file(self, path: Path) -> List[EngineeringPolicy]:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        policy_items = raw.get("policies", [raw]) if isinstance(raw, dict) else raw
        if not isinstance(policy_items, list):
            raise ValueError(f"Invalid policy schema in {path}: expected a list of policies")

        version = raw.get("version", "1.0.0") if isinstance(raw, dict) else "1.0.0"
        return [self._parse_policy(item, path, str(version)) for item in policy_items]

    def _parse_policy(self, item: Any, source_path: Path, version: str) -> EngineeringPolicy:
        if not isinstance(item, dict):
            raise ValueError(f"Invalid policy entry in {source_path}: expected mapping")

        required_fields = ("id", "name", "description", "applies_to", "rules")
        missing = [field for field in required_fields if field not in item]
        if missing:
            raise ValueError(
                f"Invalid policy entry in {source_path}: missing required fields {', '.join(missing)}"
            )

        applies_to = item["applies_to"]
        rules = item["rules"]
        if not isinstance(applies_to, list) or not all(isinstance(entry, str) for entry in applies_to):
            raise ValueError(f"Invalid applies_to in {source_path} for policy {item['id']}")
        if not isinstance(rules, list) or not all(isinstance(entry, dict) for entry in rules):
            raise ValueError(f"Invalid rules in {source_path} for policy {item['id']}")

        return EngineeringPolicy(
            id=str(item["id"]),
            name=str(item["name"]),
            description=str(item["description"]),
            applies_to=tuple(applies_to),
            rules=tuple(rules),
            version=str(item.get("version", version)),
        )
