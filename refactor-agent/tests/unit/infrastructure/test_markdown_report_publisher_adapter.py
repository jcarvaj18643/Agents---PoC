"""Unit tests for MarkdownReportPublisherAdapter."""

from datetime import datetime, timezone
from pathlib import Path

from app.domain.entities.changed_file import ChangedFile
from app.domain.entities.refactor_patch import RefactorPatch
from app.domain.entities.changed_symbol import ChangedSymbol
from app.domain.entities.refactor_suggestion import RefactorSuggestion
from app.domain.value_objects.agent_run_result import AgentRunResult
from app.domain.value_objects.engineering_policy import EngineeringPolicy
from app.domain.value_objects.pull_request_comment_publication import (
    PullRequestCommentPublication,
)
from app.domain.value_objects.pull_request_publication import PullRequestPublication
from app.domain.value_objects.project_profile import ProjectProfile
from app.domain.value_objects.review_branch_materialization import (
    ReviewBranchMaterialization,
)
from app.domain.value_objects.validation_result import ValidationResult
from app.infrastructure.adapters.reporting.markdown_report_publisher_adapter import (
    MarkdownReportPublisherAdapter,
)
from app.domain.enums.change_type import ChangeType
from app.domain.enums.language import Language
from app.domain.enums.severity import Severity
from app.domain.enums.refactor_status import RefactorStatus

class TestMarkdownReportPublisherAdapter:
    def test_renders_profile_policy_and_context_sections(self, tmp_path: Path) -> None:
        adapter = MarkdownReportPublisherAdapter(tmp_path)
        result = AgentRunResult(
            run_id="report-test",
            success=True,
            completed_at=datetime.now(timezone.utc),
            changed_files=[
                ChangedFile(
                    path=Path("app.py"),
                    change_type=ChangeType.MODIFIED,
                    language=Language.PYTHON,
                    diff_content="diff",
                    added_lines=1,
                    removed_lines=1,
                    changed_line_numbers=(3,),
                    context_snapshot="def run() -> int:\n    return 1\n",
                    symbol_context="class Service:\n    def run() -> int:\n        return 1\n",
                    full_file_context="def helper() -> int:\n    return 2\n\ndef run() -> int:\n    return 1\n",
                    impacted_symbol=ChangedSymbol(
                        name="run",
                        symbol_type="function",
                        change_type=ChangeType.MODIFIED,
                        file_path="app.py",
                        start_line=3,
                        end_line=4,
                    ),
                )
            ],
            project_profile=ProjectProfile(
                name="python",
                language="python",
                framework=None,
                test_framework="pytest",
                has_type_hints=True,
                detected_patterns=("marker:python:pyproject.toml",),
            ),
            applied_policies=[
                EngineeringPolicy(
                    id="python-docs",
                    name="Python Docs",
                    description="Document python code",
                    applies_to=("*.py",),
                    rules=({"type": "documentation", "instruction": "Add docstrings"},),
                )
            ],
            llm_stage_modes={
                "documentation": "LLM real",
                "refactor": "fallback local",
            },
            refactor_suggestions=[
                RefactorSuggestion(
                    id="suggestion-1",
                    title="Extract helper",
                    description="Split parsing and orchestration.",
                    file_path="app.py",
                    severity=Severity.INFO,
                    rationale="The diff concentrates multiple responsibilities.",
                    rule_reference="python-refactor",
                    evidence_scope="changed-hunk+symbol+full-file",
                    change_anchor="return 1",
                    impacted_symbol="run",
                )
            ],
            refactor_patches=[
                RefactorPatch(
                    suggestion_id="suggestion-1",
                    file_path=Path("app.py"),
                    original_chunk="return 1",
                    patched_chunk="return run_helper()",
                    status=RefactorStatus.VALIDATED,
                )
            ],
            review_branch=ReviewBranchMaterialization(
                branch_name="ticket123_refactor",
                commit_sha="abc123",
                pushed=True,
                remote_ref="origin/ticket123_refactor",
                committed_files=("app.py",),
            ),
            review_branch_validation_result=ValidationResult.safe(
                executed_checks=["TEST:app.py -> pytest -q tests/test_app.py"],
                summary="Generated branch validation passed.",
            ),
            review_pull_request=PullRequestPublication(
                number=99,
                url="https://github.com/acme/refactor-agent/pull/99",
                head_branch="ticket123_refactor",
                base_branch="main",
                created=True,
            ),
            pull_request_comment=PullRequestCommentPublication(
                comment_id=1234,
                url="https://github.com/acme/refactor-agent/pull/99#issuecomment-1234",
                updated=False,
            ),
            validation_result=ValidationResult.skipped(
                planned_checks=["LINT:app.py -> ruff check app.py"],
                summary="Validation was intentionally deferred to CI/CD; the agent did not execute commands in the target repository.",
            ),
        )

        report_path = adapter.publish(result)
        report_content = Path(report_path).read_text(encoding="utf-8")

        assert "## Project Profile" in report_content
        assert "## Applied Policies" in report_content
        assert "## LLM Execution Summary" in report_content
        assert "## Changed File Scope" in report_content
        assert "## Context Preview" in report_content
        assert "## Refactor Suggestions" in report_content
        assert "## Refactor Patch Preview" in report_content
        assert "## Review Branch Materialization" in report_content
        assert "## Review Branch Validation" in report_content
        assert "## Review Pull Request" in report_content
        assert "## Pull Request Comment Publication" in report_content
        assert "**Run status:** `completed`" in report_content
        assert "**Governance status:** `eligible`" in report_content
        assert "**Status:** skipped" in report_content
        assert "deferred to CI/CD" in report_content
        assert "Extract helper" in report_content
        assert "status=`validated`" in report_content
        assert "ticket123_refactor" in report_content
        assert "origin/ticket123_refactor" in report_content
        assert "Generated branch validation passed." in report_content
        assert "https://github.com/acme/refactor-agent/pull/99" in report_content
        assert "issuecomment-1234" in report_content
        assert "Changed hunk focus" in report_content
        assert "**Changed lines:** 3" in report_content
        assert "Impacted symbol context" in report_content
        assert "Full file context" in report_content
        assert "symbol=`run`" in report_content
        assert "evidence=`changed-hunk+symbol+full-file`" in report_content
        assert "Planned CI/CD checks" in report_content
        assert "**Documentation**: `LLM real`" in report_content
        assert "**Refactor**: `fallback local`" in report_content
        assert "def run() -> int:" in report_content