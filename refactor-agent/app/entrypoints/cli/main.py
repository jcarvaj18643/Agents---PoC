"""CLI entrypoint for the Engineering Governance Agent.

Usage:
    python -m app.entrypoints.cli.main \
        --repo-path /path/to/repo \
        --base-ref main \
        --head-ref feature/my-branch \
        [--dry-run | --no-dry-run]
"""

import argparse
import sys
import uuid
from pathlib import Path

# Ensure project root is on sys.path when run directly (python app/entrypoints/cli/main.py)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app.application.dto.agent_run_request import AgentRunRequest  # noqa: E402
from app.bootstrap.container import build_container  # noqa: E402
from app.infrastructure.logging.console_logger import get_logger  # noqa: E402

logger = get_logger("cli")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Engineering Governance Agent — local CLI runner",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--repo-path",
        required=True,
        help="Absolute or relative path to the repository root",
    )
    parser.add_argument(
        "--base-ref",
        required=True,
        help="Base git ref to diff against (e.g. 'main', 'origin/main')",
    )
    parser.add_argument(
        "--head-ref",
        required=True,
        help="Head git ref representing the changes (e.g. 'HEAD', branch name, or 'WORKTREE' for local uncommitted changes)",
    )
    parser.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Analyse only; do not write report or apply any changes",
    )
    parser.add_argument(
        "--apply-refactors",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Apply validated refactor patches to the local checkout when executable patch data is available",
    )
    parser.add_argument(
        "--publish-review-branch",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Materialize approved refactor patches into a dedicated review branch",
    )
    parser.add_argument(
        "--push-review-branch",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Push the review branch to the configured remote after committing approved patches",
    )
    parser.add_argument(
        "--review-branch-name",
        default=None,
        help="Explicit name for the review branch; otherwise a deterministic *_refactor name is generated",
    )
    parser.add_argument(
        "--review-remote-name",
        default="origin",
        help="Remote name used when pushing the review branch",
    )
    parser.add_argument(
        "--publish-pr-comment",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Publish or update an Engineering Governance summary comment on a pull request",
    )
    parser.add_argument(
        "--create-review-pull-request",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Create or reuse a pull request for the materialized review branch",
    )
    parser.add_argument(
        "--repository",
        default=None,
        help="GitHub repository in owner/name format, required for PR creation or comment publication",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    container = build_container()

    request = AgentRunRequest(
        repo_path=args.repo_path,
        base_ref=args.base_ref,
        head_ref=args.head_ref,
        run_id=str(uuid.uuid4()),
        triggered_by="cli",
        dry_run=args.dry_run,
        apply_refactors=args.apply_refactors,
        publish_review_branch=args.publish_review_branch,
        push_review_branch=args.push_review_branch,
        review_branch_name=args.review_branch_name,
        review_remote_name=args.review_remote_name,
        repository=args.repository,
        publish_pr_comment=args.publish_pr_comment,
        create_review_pull_request=args.create_review_pull_request,
    )

    logger.info(
        "Starting governance agent [run_id=%s, dry_run=%s, apply_refactors=%s, publish_review_branch=%s, push_review_branch=%s, publish_pr_comment=%s, create_review_pull_request=%s]",
        request.run_id,
        request.dry_run,
        request.apply_refactors,
        request.publish_review_branch,
        request.push_review_branch,
        request.publish_pr_comment,
        request.create_review_pull_request,
    )
    response = container.governance_agent.run(request)

    if response.success:
        logger.info("Run completed. Report: %s", response.result and response.result.report_path)
        sys.exit(0)
    else:
        logger.error("Run failed: %s", response.error)
        sys.exit(1)


if __name__ == "__main__":
    main()
