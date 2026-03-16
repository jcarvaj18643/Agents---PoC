from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.application.dto.agent_run_response import AgentRunResponse
from app.domain.value_objects.agent_run_result import AgentRunResult
from app.domain.value_objects.validation_result import ValidationResult
from app.entrypoints.github_actions import runner


class _FakeGitHubContext:
    def __init__(self) -> None:
        self._payload = {}

    def get_base_ref(self) -> str:
        return "base-sha-123"

    def get_base_branch(self) -> str:
        return "main"

    def get_head_ref(self) -> str:
        return "head-sha-456"

    def get_head_branch(self) -> str:
        return "feature/refactor"

    def get_repository(self) -> str:
        return "acme/refactor-agent"

    def get_pull_request_number(self) -> int:
        return 123

    def get_event_payload(self) -> dict:
        return self._payload


class _FakeGovernanceAgent:
    def __init__(self, response: AgentRunResponse) -> None:
        self._response = response
        self.requests = []

    def run(self, request):  # type: ignore[no-untyped-def]
        self.requests.append(request)
        return self._response


@dataclass
class _FakeContainer:
    governance_agent: _FakeGovernanceAgent
    github_context_provider: _FakeGitHubContext


class TestGitHubActionsRunner:
    def test_writes_outputs_and_summary_on_success(self, monkeypatch, tmp_path: Path) -> None:
        output_path = tmp_path / "github_output.txt"
        summary_path = tmp_path / "github_summary.md"
        result = AgentRunResult(
            run_id="run-123",
            success=True,
            completed_at=datetime.now(timezone.utc),
            report_path="/tmp/report.md",
            validation_result=ValidationResult.skipped(
                summary="Validation was intentionally deferred to CI/CD.",
            ),
        )
        fake_agent = _FakeGovernanceAgent(AgentRunResponse(success=True, result=result))
        fake_container = _FakeContainer(fake_agent, _FakeGitHubContext())

        monkeypatch.setattr(runner, "build_container", lambda: fake_container)
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
        monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_path))
        monkeypatch.setenv("GITHUB_BASE_BRANCH", "main")
        monkeypatch.setenv("GITHUB_HEAD_BRANCH", "feature/refactor")
        monkeypatch.chdir(tmp_path)

        with pytest.raises(SystemExit) as exit_info:
            runner.main()

        assert exit_info.value.code == 0
        output_content = output_path.read_text(encoding="utf-8")
        summary_content = summary_path.read_text(encoding="utf-8")
        assert "success<<__GH_EOF__" in output_content
        assert "true" in output_content
        assert "governance_status<<__GH_EOF__" in output_content
        assert "deferred-to-ci" in output_content
        assert "report_path<<__GH_EOF__" in output_content
        assert "/tmp/report.md" in output_content
        assert "review_pull_request_url<<__GH_EOF__" in output_content
        assert "pull_request_comment_url<<__GH_EOF__" in output_content
        assert "## Engineering Governance Agent" in summary_content
        assert "Target branch: `main`" in summary_content
        assert "Current branch: `feature/refactor`" in summary_content
        assert "Diff refs: `base-sha-123` -> `head-sha-456`" in summary_content
        assert "Run status: `completed`" in summary_content
        assert "Governance status: `deferred-to-ci`" in summary_content
        assert fake_agent.requests[0].pull_request_number == 123
        assert fake_agent.requests[0].repository == "acme/refactor-agent"
        assert fake_agent.requests[0].base_branch == "main"
        assert fake_agent.requests[0].head_branch == "feature/refactor"
        assert fake_agent.requests[0].publish_pr_comment is True
        assert fake_agent.requests[0].base_ref == "base-sha-123"
        assert fake_agent.requests[0].head_ref == "head-sha-456"

    def test_fails_fast_when_openai_secret_is_missing_in_github_actions(self, monkeypatch, tmp_path: Path) -> None:
        output_path = tmp_path / "github_output.txt"
        summary_path = tmp_path / "github_summary.md"

        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
        monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_path))
        monkeypatch.setenv("GITHUB_BASE_BRANCH", "main")
        monkeypatch.setenv("GITHUB_HEAD_BRANCH", "feature/refactor")

        with pytest.raises(SystemExit) as exit_info:
            runner.main()

        assert exit_info.value.code == 1
        output_content = output_path.read_text(encoding="utf-8")
        summary_content = summary_path.read_text(encoding="utf-8")
        assert "success<<__GH_EOF__" in output_content
        assert "false" in output_content
        assert "OPENAI_API_KEY" in output_content
        assert "failed before execution" in summary_content
        assert "OPENAI_API_KEY" in summary_content