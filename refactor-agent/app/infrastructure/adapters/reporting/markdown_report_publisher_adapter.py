from datetime import datetime, timezone
from pathlib import Path

from app.application.ports.outbound.report_publisher_port import ReportPublisherPort
from app.domain.entities.changed_file import ChangedFile
from app.domain.entities.refactor_patch import RefactorPatch
from app.domain.value_objects.agent_run_result import AgentRunResult
from app.infrastructure.logging.console_logger import get_logger

logger = get_logger(__name__)

_TEXT_BLOCK_START = "```text"
_TEXT_BLOCK_END = "```"


class MarkdownReportPublisherAdapter(ReportPublisherPort):
    """Adapter: serialises an AgentRunResult into a Markdown file on disk.

    TODO: add rich formatting, tables, diff-block syntax highlighting,
    and an optional GitHub PR comment integration.
    """

    def __init__(self, output_dir: Path) -> None:
        self._output_dir = output_dir

    def publish(self, result: AgentRunResult) -> str:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        filename = f"report_{result.run_id}_{timestamp}.md"
        report_path = self._output_dir / filename

        content = self._render(result)
        report_path.write_text(content, encoding="utf-8")
        logger.info("Report published: %s", report_path)
        return str(report_path)

    def _render(self, result: AgentRunResult) -> str:
        lines = [
            "# Engineering Governance Agent Report",
            "",
            f"**Run ID:** `{result.run_id}`",
            f"**Run status:** `{result.execution_status}`",
            f"**Governance status:** `{result.governance_status}`",
            f"**Completed at:** {result.completed_at.isoformat()}",
            "",
            "---",
            "",
            "## Scope Overview",
            "",
            f"**Changed files:** {len(result.changed_files)}",
            f"**Applied policies:** {len(result.applied_policies)}",
            "",
        ]

        lines += self._render_project_profile(result)
        lines += self._render_applied_policies(result)
        lines += self._render_llm_execution_summary(result)
        lines += self._render_changed_file_scope(result)
        lines += self._render_documentation_artifacts(result)
        lines += self._render_refactor_suggestions(result)
        lines += self._render_refactor_patches(result)
        lines += self._render_review_branch(result)
        lines += self._render_review_pull_request(result)
        lines += self._render_pull_request_comment(result)
        lines += self._render_validation(result)

        lines.append("")
        return "\n".join(lines)

    def _render_project_profile(self, result: AgentRunResult) -> list[str]:
        if not result.project_profile:
            return []

        lines = [
            "## Project Profile",
            "",
            f"**Profile:** `{result.project_profile.name}`",
            f"**Language:** `{result.project_profile.language}`",
            f"**Framework:** `{result.project_profile.framework or 'n/a'}`",
            f"**Test framework:** `{result.project_profile.test_framework or 'n/a'}`",
            f"**Type hints:** `{result.project_profile.has_type_hints}`",
        ]
        if result.project_profile.detected_patterns:
            lines += ["", "**Detected patterns:**"]
            lines += [f"- `{pattern}`" for pattern in result.project_profile.detected_patterns]
        lines.append("")
        return lines

    def _render_applied_policies(self, result: AgentRunResult) -> list[str]:
        lines = [
            "## Applied Policies",
            "",
        ]
        if result.applied_policies:
            lines += [
                f"- **{policy.name}** (`{policy.id}`) — {policy.description}"
                for policy in result.applied_policies
            ]
        else:
            lines.append("_No engineering policies loaded._")
        lines.append("")
        return lines

    def _render_llm_execution_summary(self, result: AgentRunResult) -> list[str]:
        lines = [
            "## LLM Execution Summary",
            "",
        ]
        if result.llm_stage_modes:
            lines += [
                f"- **{stage.replace('_', ' ').title()}**: `{mode}`"
                for stage, mode in result.llm_stage_modes.items()
            ]
        else:
            lines.append("_No LLM-backed stages were recorded for this run._")
        lines.append("")
        return lines

    def _render_changed_file_scope(self, result: AgentRunResult) -> list[str]:
        lines = [
            "## Changed File Scope",
            "",
        ]
        if result.changed_files:
            lines += [
                "| File | Change | Language | +Lines | -Lines |",
                "| --- | --- | --- | ---: | ---: |",
            ]
            lines += [
                f"| `{changed_file.path.as_posix()}` | `{changed_file.change_type.value}` | `{changed_file.language.value}` | {changed_file.added_lines} | {changed_file.removed_lines} |"
                for changed_file in result.changed_files
            ]
            lines += ["", "## Context Preview", ""]
            for changed_file in result.changed_files:
                lines += self._render_context_preview(changed_file)
        else:
            lines.append("_No changed files detected._")
        lines.append("")
        return lines

    def _render_documentation_artifacts(self, result: AgentRunResult) -> list[str]:
        lines = [
            "## Documentation Artifacts",
            "",
        ]
        if result.documentation_artifacts:
            lines += [
                f"- `{artifact.file_path}` (model=`{artifact.model_used}`, tokens={artifact.tokens_used})"
                for artifact in result.documentation_artifacts
            ]
        else:
            lines.append("_No documentation artifacts generated._")
        lines.append("")
        return lines

    def _render_refactor_suggestions(self, result: AgentRunResult) -> list[str]:
        lines = [
            "## Refactor Suggestions",
            "",
        ]
        if result.refactor_suggestions:
            lines += [self._render_refactor_suggestion_line(suggestion) for suggestion in result.refactor_suggestions]
        else:
            lines.append("_No refactor suggestions generated._")
        lines.append("")
        return lines

    def _render_refactor_suggestion_line(self, suggestion) -> str:
        details: list[str] = []
        if suggestion.evidence_scope:
            details.append(f"evidence=`{suggestion.evidence_scope}`")
        if suggestion.impacted_symbol:
            details.append(f"symbol=`{suggestion.impacted_symbol}`")
        if suggestion.change_anchor:
            details.append(f"anchor=`{suggestion.change_anchor}`")
        suffix = f" ({', '.join(details)})" if details else ""
        return f"- **[{suggestion.severity.value.upper()}]** {suggestion.title} — `{suggestion.file_path}`{suffix}"

    def _render_refactor_patches(self, result: AgentRunResult) -> list[str]:
        lines = [
            "## Refactor Patch Preview",
            "",
        ]
        if result.refactor_patches:
            lines += [self._render_refactor_patch_line(patch) for patch in result.refactor_patches]
        else:
            lines.append("_No executable refactor patches were prepared for this run._")
        lines.append("")
        return lines

    def _render_refactor_patch_line(self, patch: RefactorPatch) -> str:
        applied_label = "applied" if patch.applied else "not-applied"
        anchor = patch.original_chunk[:80] if patch.original_chunk else "n/a"
        return (
            f"- `{patch.file_path.as_posix()}` status=`{patch.status.value}` "
            f"apply=`{applied_label}` anchor=`{anchor}`"
        )

    def _render_validation(self, result: AgentRunResult) -> list[str]:
        validation_result = result.validation_result
        if not validation_result:
            return []

        lines = [
            "## Validation",
            "",
            f"**Status:** {validation_result.status.value}",
        ]
        if validation_result.summary:
            lines.append(f"**Summary:** {validation_result.summary}")
        lines.append(f"**Eligibility:** {self._render_validation_eligibility(validation_result)}")
        if validation_result.issues:
            lines += ["", "| Code | Severity | Message |", "| --- | --- | --- |"]
            lines += [
                f"| `{i.code}` | {i.severity.value} | {i.message} |"
                for i in validation_result.issues
            ]
        if validation_result.planned_checks:
            lines += ["", "**Planned CI/CD checks:**"]
            lines += [f"- `{check}`" for check in validation_result.planned_checks]
        if validation_result.executed_checks:
            lines += ["", "**Executed checks:**"]
            lines += [f"- `{check}`" for check in validation_result.executed_checks]
        return lines

    def _render_review_branch(self, result: AgentRunResult) -> list[str]:
        lines = [
            "## Review Branch Materialization",
            "",
        ]
        if result.review_branch is None:
            lines.append("_No review branch was materialized for this run._")
            lines.append("")
            return lines

        lines += [
            f"- Branch: `{result.review_branch.branch_name}`",
            f"- Commit: `{result.review_branch.commit_sha}`",
            f"- Pushed: `{result.review_branch.pushed}`",
            f"- Remote ref: `{result.review_branch.remote_ref or 'not-pushed'}`",
        ]
        if result.review_branch.committed_files:
            lines += ["", "**Committed files:**"]
            lines += [f"- `{file_path}`" for file_path in result.review_branch.committed_files]
        lines.append("")
        return lines

    def _render_review_pull_request(self, result: AgentRunResult) -> list[str]:
        lines = [
            "## Review Pull Request",
            "",
        ]
        if result.review_pull_request is None:
            lines.append("_No review pull request was created for this run._")
            lines.append("")
            return lines

        lines += [
            f"- PR number: `{result.review_pull_request.number}`",
            f"- URL: `{result.review_pull_request.url}`",
            f"- Head branch: `{result.review_pull_request.head_branch}`",
            f"- Base branch: `{result.review_pull_request.base_branch}`",
            f"- Created: `{result.review_pull_request.created}`",
            "",
        ]
        return lines

    def _render_pull_request_comment(self, result: AgentRunResult) -> list[str]:
        lines = [
            "## Pull Request Comment Publication",
            "",
        ]
        if result.pull_request_comment is None:
            lines.append("_No pull request comment was published for this run._")
            lines.append("")
            return lines

        lines += [
            f"- Comment ID: `{result.pull_request_comment.comment_id}`",
            f"- URL: `{result.pull_request_comment.url}`",
            f"- Updated existing comment: `{result.pull_request_comment.updated}`",
            "",
        ]
        return lines

    def _render_context_preview(self, changed_file: ChangedFile) -> list[str]:
        lines = [f"### `{changed_file.path.as_posix()}`", ""]
        if changed_file.changed_hunk_context:
            lines += self._render_text_block("Changed hunk focus", changed_file.changed_hunk_context)
        else:
            lines += ["_No changed-hunk context available for this file._", ""]

        if changed_file.changed_line_numbers:
            lines += [f"**Changed lines:** {', '.join(str(line) for line in changed_file.changed_line_numbers[:12])}", ""]

        if changed_file.impacted_symbol is not None:
            lines += [
                f"**Impacted symbol** `{changed_file.impacted_symbol.symbol_type}` `{changed_file.impacted_symbol.name}` "
                f"(lines {changed_file.impacted_symbol.start_line}-{changed_file.impacted_symbol.end_line})",
                "",
            ]

        if changed_file.symbol_context and changed_file.symbol_context != changed_file.changed_hunk_context:
            lines += self._render_text_block("Impacted symbol context", changed_file.symbol_context)
        else:
            lines += ["_No additional symbol context available for this file._", ""]

        if (
            changed_file.full_file_context
            and changed_file.full_file_context != changed_file.changed_hunk_context
            and changed_file.full_file_context != changed_file.symbol_context
        ):
            lines += self._render_text_block("Full file context", changed_file.full_file_context)
        else:
            lines += ["_No additional full-file context available for this file._", ""]
        return lines

    def _render_validation_eligibility(self, validation_result) -> str:
        if validation_result.deferred:
            return "deferred to CI/CD"
        return "eligible" if validation_result.passed else "blocked"

    def _render_text_block(self, title: str, content: str) -> list[str]:
        return [f"**{title}**", "", _TEXT_BLOCK_START, content.strip(), _TEXT_BLOCK_END, ""]
