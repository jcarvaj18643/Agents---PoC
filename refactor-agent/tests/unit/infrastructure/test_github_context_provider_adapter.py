import json

from app.infrastructure.adapters.github.github_context_provider_adapter import (
    GitHubContextProviderAdapter,
)


class TestGitHubContextProviderAdapter:
    def test_prefers_explicit_environment_values(self, monkeypatch, tmp_path) -> None:
        event_path = tmp_path / "event.json"
        event_path.write_text("{}", encoding="utf-8")
        monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))
        monkeypatch.setenv("GITHUB_BASE_REF", "release")
        monkeypatch.setenv("GITHUB_HEAD_REF", "feature/refactor")
        monkeypatch.setenv("GITHUB_BASE_BRANCH", "release")
        monkeypatch.setenv("GITHUB_HEAD_BRANCH", "feature/refactor")
        monkeypatch.setenv("GITHUB_REPOSITORY", "acme/refactor-agent")
        monkeypatch.setenv("GITHUB_PR_NUMBER", "42")

        adapter = GitHubContextProviderAdapter()

        assert adapter.get_base_ref() == "release"
        assert adapter.get_base_branch() == "release"
        assert adapter.get_head_ref() == "feature/refactor"
        assert adapter.get_head_branch() == "feature/refactor"
        assert adapter.get_repository() == "acme/refactor-agent"
        assert adapter.get_pull_request_number() == 42

    def test_falls_back_to_pull_request_payload(self, monkeypatch, tmp_path) -> None:
        event_path = tmp_path / "event.json"
        event_path.write_text(
            json.dumps(
                {
                    "number": 17,
                    "pull_request": {
                        "number": 17,
                        "base": {"ref": "main", "sha": "base-sha-123"},
                        "head": {"ref": "feature/reporting", "sha": "head-sha-456"},
                    },
                    "repository": {
                        "full_name": "acme/backend",
                        "default_branch": "main",
                    },
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.delenv("GITHUB_BASE_REF", raising=False)
        monkeypatch.delenv("GITHUB_HEAD_REF", raising=False)
        monkeypatch.delenv("GITHUB_BASE_BRANCH", raising=False)
        monkeypatch.delenv("GITHUB_HEAD_BRANCH", raising=False)
        monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
        monkeypatch.delenv("GITHUB_PR_NUMBER", raising=False)
        monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))

        adapter = GitHubContextProviderAdapter()

        assert adapter.get_base_ref() == "base-sha-123"
        assert adapter.get_base_branch() == "main"
        assert adapter.get_head_ref() == "head-sha-456"
        assert adapter.get_head_branch() == "feature/reporting"
        assert adapter.get_repository() == "acme/backend"
        assert adapter.get_pull_request_number() == 17

    def test_falls_back_to_workflow_dispatch_inputs(self, monkeypatch, tmp_path) -> None:
        event_path = tmp_path / "event.json"
        event_path.write_text(
            json.dumps(
                {
                    "inputs": {
                        "base_ref": "develop",
                        "head_ref": "HEAD",
                    },
                    "repository": {
                        "full_name": "acme/backend",
                        "default_branch": "main",
                    },
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.delenv("GITHUB_BASE_REF", raising=False)
        monkeypatch.delenv("GITHUB_HEAD_REF", raising=False)
        monkeypatch.delenv("GITHUB_BASE_BRANCH", raising=False)
        monkeypatch.delenv("GITHUB_HEAD_BRANCH", raising=False)
        monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))

        adapter = GitHubContextProviderAdapter()

        assert adapter.get_base_ref() == "develop"
        assert adapter.get_base_branch() == "develop"
        assert adapter.get_head_ref() == "HEAD"
        assert adapter.get_head_branch() == "HEAD"
