import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from app.application.ports.outbound.github_context_provider_port import (
    GitHubContextProviderPort,
)
from app.infrastructure.logging.console_logger import get_logger

logger = get_logger(__name__)


class GitHubContextProviderAdapter(GitHubContextProviderPort):
    """Adapter: reads GitHub Actions runtime context from environment variables.

    All environment variable names follow the standard GitHub Actions conventions.
    Outside of CI the values fall back to safe defaults so the agent can still
    run in local/dry-run mode.
    """

    def get_base_ref(self) -> str:
        env_value = os.getenv("GITHUB_BASE_REF")
        if env_value:
            return env_value

        payload = self.get_event_payload()
        pull_request_sha = self._get_nested_str(payload, "pull_request", "base", "sha")
        if pull_request_sha:
            return pull_request_sha

        pull_request_ref = self._get_nested_str(payload, "pull_request", "base", "ref")
        if pull_request_ref:
            return pull_request_ref

        input_ref = self._get_nested_str(payload, "inputs", "base_ref")
        if input_ref:
            return input_ref

        default_branch = self._get_nested_str(payload, "repository", "default_branch")
        if default_branch:
            return default_branch

        return "main"

    def get_base_branch(self) -> str:
        env_value = os.getenv("GITHUB_BASE_BRANCH")
        if env_value:
            return env_value

        payload = self.get_event_payload()
        pull_request_ref = self._get_nested_str(payload, "pull_request", "base", "ref")
        if pull_request_ref:
            return pull_request_ref

        input_ref = self._get_nested_str(payload, "inputs", "base_ref")
        if input_ref:
            return input_ref

        default_branch = self._get_nested_str(payload, "repository", "default_branch")
        if default_branch:
            return default_branch

        return "main"

    def get_head_ref(self) -> str:
        env_value = os.getenv("GITHUB_HEAD_REF")
        if env_value:
            return env_value

        payload = self.get_event_payload()
        pull_request_sha = self._get_nested_str(payload, "pull_request", "head", "sha")
        if pull_request_sha:
            return pull_request_sha

        pull_request_ref = self._get_nested_str(payload, "pull_request", "head", "ref")
        if pull_request_ref:
            return pull_request_ref

        input_ref = self._get_nested_str(payload, "inputs", "head_ref")
        if input_ref:
            return input_ref

        return "HEAD"

    def get_head_branch(self) -> str:
        env_value = os.getenv("GITHUB_HEAD_BRANCH")
        if env_value:
            return env_value

        payload = self.get_event_payload()
        pull_request_ref = self._get_nested_str(payload, "pull_request", "head", "ref")
        if pull_request_ref:
            return pull_request_ref

        input_ref = self._get_nested_str(payload, "inputs", "head_ref")
        if input_ref:
            return input_ref

        return "HEAD"

    def get_repository(self) -> str:
        env_value = os.getenv("GITHUB_REPOSITORY")
        if env_value:
            return env_value

        payload = self.get_event_payload()
        full_name = self._get_nested_str(payload, "repository", "full_name")
        if full_name:
            return full_name
        return ""

    def get_pull_request_number(self) -> Optional[int]:
        raw = os.getenv("GITHUB_PR_NUMBER")
        if raw and raw.isdigit():
            return int(raw)

        payload = self.get_event_payload()
        pull_request = payload.get("pull_request")
        if isinstance(pull_request, dict):
            number = pull_request.get("number")
            if isinstance(number, int):
                return number

        number = payload.get("number")
        if isinstance(number, int):
            return number
        return None

    def _get_nested_str(self, payload: Dict[str, Any], *keys: str) -> str:
        current: Any = payload
        for key in keys:
            if not isinstance(current, dict):
                return ""
            current = current.get(key)
        return current if isinstance(current, str) else ""

    def get_event_payload(self) -> Dict[str, Any]:
        event_path = os.getenv("GITHUB_EVENT_PATH")
        if event_path:
            path = Path(event_path)
            if path.exists():
                try:
                    with path.open(encoding="utf-8") as fh:
                        return json.load(fh)  # type: ignore[no-any-return]
                except (json.JSONDecodeError, OSError) as exc:
                    logger.warning("Could not read event payload: %s", exc)
        return {}
