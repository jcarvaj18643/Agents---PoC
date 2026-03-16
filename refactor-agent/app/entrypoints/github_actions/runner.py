"""GitHub Actions entrypoint for the Engineering Governance Agent.

This module is invoked by the CI workflow. It reads all runtime context
(refs, repo, PR number) from the GitHub Actions environment variables via
GitHubContextProviderAdapter and delegates execution to the same
RunEngineeringGovernanceAgentUseCase used by the CLI.

The entrypoint owns only:
 - reading CI context
 - constructing the AgentRunRequest
 - wiring the container
 - translating the response to an exit code
"""

import os
import sys
import uuid
from pathlib import Path

# Ensure project root is on sys.path when invoked by the actions runner
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app.application.dto.agent_run_request import AgentRunRequest  # noqa: E402
from app.bootstrap.container import build_container  # noqa: E402
from app.infrastructure.logging.console_logger import get_logger  # noqa: E402

logger = get_logger("github_actions_runner")

_STEP_SUMMARY_TITLE = "## Engineering Governance Agent"


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _append_step_summary(lines: list[str]) -> None:
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    with Path(summary_path).open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def _write_github_outputs(values: dict[str, str]) -> None:
    output_path = os.getenv("GITHUB_OUTPUT")
    if not output_path:
        return

    with Path(output_path).open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}<<__GH_EOF__\n{value}\n__GH_EOF__\n")


def _fail_configuration(message: str) -> None:
    logger.error(message)
    _write_github_outputs({"success": "false", "error": message})
    _append_step_summary([
        _STEP_SUMMARY_TITLE,
        "",
        "**Status:** failed before execution",
        f"**Reason:** {message}",
    ])
    sys.exit(1)


def _validate_actions_configuration() -> None:
    if os.getenv("GITHUB_ACTIONS", "").lower() != "true":
        return

    if not os.getenv("OPENAI_API_KEY"):
        _fail_configuration(
            "Missing required GitHub Actions secret: OPENAI_API_KEY. The CI workflow requires an explicit LLM credential."
        )


def _publish_success_metadata(request: AgentRunRequest, response) -> None:  # type: ignore[no-untyped-def]
    result = response.result
    if result is None:
        return

    validation_status = result.validation_result.status.value if result.validation_result else "not-evaluated"
    review_branch_validation_status = (
        result.review_branch_validation_result.status.value
        if result.review_branch_validation_result
        else "not-run"
    )
    report_path = result.report_path or ""
    _write_github_outputs(
        {
            "success": "true",
            "run_id": request.run_id,
            "report_path": report_path,
            "governance_status": result.governance_status,
            "validation_status": validation_status,
            "review_branch_validation_status": review_branch_validation_status,
            "review_branch_name": result.review_branch.branch_name if result.review_branch else "",
            "review_pull_request_url": result.review_pull_request.url if result.review_pull_request else "",
            "pull_request_comment_url": result.pull_request_comment.url if result.pull_request_comment else "",
        }
    )
    _append_step_summary(
        [
            _STEP_SUMMARY_TITLE,
            "",
            f"- Run ID: `{request.run_id}`",
            f"- Target branch: `{os.getenv('GITHUB_BASE_BRANCH', request.base_ref)}`",
            f"- Current branch: `{os.getenv('GITHUB_HEAD_BRANCH', request.head_ref)}`",
            f"- Diff refs: `{request.base_ref}` -> `{request.head_ref}`",
            f"- Run status: `{result.execution_status}`",
            f"- Governance status: `{result.governance_status}`",
            f"- Validation status: `{validation_status}`",
            f"- Review branch validation: `{review_branch_validation_status}`",
            f"- Report: `{report_path or 'not-published'}`",
            f"- Review PR: `{result.review_pull_request.url if result.review_pull_request else 'not-created'}`",
            f"- PR comment: `{result.pull_request_comment.url if result.pull_request_comment else 'not-published'}`",
        ]
    )


def _publish_failure_metadata(request: AgentRunRequest, error: str) -> None:
    _write_github_outputs(
        {
            "success": "false",
            "run_id": request.run_id,
            "error": error,
        }
    )
    _append_step_summary(
        [
            _STEP_SUMMARY_TITLE,
            "",
            f"- Run ID: `{request.run_id}`",
            f"- Target branch: `{os.getenv('GITHUB_BASE_BRANCH', request.base_ref)}`",
            f"- Current branch: `{os.getenv('GITHUB_HEAD_BRANCH', request.head_ref)}`",
            f"- Diff refs: `{request.base_ref}` -> `{request.head_ref}`",
            "- Run status: `failed`",
            f"- Error: {error}",
        ]
    )


def main() -> None:
    _validate_actions_configuration()

    container = build_container()
    ctx = container.github_context_provider
    requested_create_review_pull_request = _env_flag("GOVERNANCE_CREATE_REVIEW_PULL_REQUEST")
    requested_validate_review_branch = _env_flag("GOVERNANCE_VALIDATE_REVIEW_BRANCH") or requested_create_review_pull_request
    requested_publish_review_branch = _env_flag("GOVERNANCE_PUBLISH_REVIEW_BRANCH") or requested_validate_review_branch
    requested_push_review_branch = _env_flag("GOVERNANCE_PUSH_REVIEW_BRANCH") or requested_create_review_pull_request

    request = AgentRunRequest(
        repo_path=str(Path.cwd()),
        base_ref=ctx.get_base_ref(),
        head_ref=ctx.get_head_ref(),
        run_id=str(uuid.uuid4()),
        triggered_by="github_actions",
        dry_run=False,
        apply_refactors=False,
        publish_review_branch=requested_publish_review_branch,
        push_review_branch=requested_push_review_branch,
        validate_review_branch=requested_validate_review_branch,
        review_branch_name=os.getenv("GOVERNANCE_REVIEW_BRANCH_NAME") or None,
        review_remote_name=os.getenv("GOVERNANCE_REVIEW_REMOTE_NAME", "origin"),
        repository=ctx.get_repository(),
        base_branch=ctx.get_base_branch(),
        head_branch=ctx.get_head_branch(),
        publish_pr_comment=ctx.get_pull_request_number() is not None,
        create_review_pull_request=requested_create_review_pull_request,
        pull_request_number=ctx.get_pull_request_number(),
    )

    logger.info(
        "GitHub Actions run [run_id=%s, repo=%s, target_branch=%s, current_branch=%s, base_ref=%s, head_ref=%s, pr=%s, publish_review_branch=%s, push_review_branch=%s, validate_review_branch=%s, create_review_pull_request=%s]",
        request.run_id,
        ctx.get_repository(),
        ctx.get_base_branch(),
        ctx.get_head_branch(),
        request.base_ref,
        request.head_ref,
        request.pull_request_number,
        request.publish_review_branch,
        request.push_review_branch,
        request.validate_review_branch,
        request.create_review_pull_request,
    )

    response = container.governance_agent.run(request)

    if response.success:
        logger.info("Run completed. Report: %s", response.result and response.result.report_path)
        _publish_success_metadata(request, response)
        sys.exit(0)
    else:
        logger.error("Run failed: %s", response.error)
        _publish_failure_metadata(request, response.error or "unknown error")
        sys.exit(1)


if __name__ == "__main__":
    main()
