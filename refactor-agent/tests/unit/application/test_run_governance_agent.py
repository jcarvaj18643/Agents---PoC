"""Unit tests for RunEngineeringGovernanceAgentUseCase (the orchestrator).

All collaborating use cases are replaced with minimal test doubles.
No I/O or network access in these tests.
"""

from pathlib import Path
from typing import List

from app.application.dto.agent_run_request import AgentRunRequest
from app.application.orchestrators.run_engineering_governance_agent import (
    ReviewAutomationFlow,
    RunEngineeringGovernanceAgentUseCase,
)
from app.domain.entities.changed_file import ChangedFile
from app.domain.entities.code_scope import CodeScope
from app.domain.entities.refactor_patch import RefactorPatch
from app.domain.enums.change_type import ChangeType
from app.domain.enums.language import Language
from app.domain.enums.refactor_status import RefactorStatus
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


# ── Test Doubles ──────────────────────────────────────────────────────────────


class _FakeAnalyzeDiff:
    def __init__(self, scope: CodeScope) -> None:
        self._scope = scope

    def execute(self, base_ref: str, head_ref: str, repo_path: str) -> CodeScope:
        return self._scope


class _FakeDetectProfile:
    def execute(self, repo_path: str) -> ProjectProfile:
        return ProjectProfile(
            name="python",
            language="python",
            framework=None,
            test_framework="pytest",
            has_type_hints=True,
        )


class _FakeFilterScope:
    def execute(self, scope: CodeScope, profile: ProjectProfile) -> CodeScope:
        return scope


class _FakeLoadPolicies:
    def execute(self, profile_name: str) -> List[EngineeringPolicy]:
        return []


class _FakeBuildContext:
    def execute(self, scope: CodeScope, repo_path: str, profile_name: str | None = None) -> List[ChangedFile]:
        return list(scope.changed_files)


class _FakeGenerateDocs:
    last_execution_mode = "not-invoked"

    def execute(self, files: list, policies: list) -> list:
        return []


class _FakeGenerateRefactors:
    last_execution_mode = "not-invoked"

    def execute(self, files: list, policies: list) -> list:
        return []


class _FakeValidateSafety:
    def execute(self, suggestions: list, changed_files: list, repo_path: str, profile: ProjectProfile) -> ValidationResult:
        return ValidationResult.safe()


class _FakePublishReport:
    def execute(self, result: object) -> str:
        return "/tmp/report.md"


class _FakeMaterializePatches:
    def __init__(self) -> None:
        self.calls: list[tuple[bool, str]] = []

    def execute(self, suggestions: list, repo_path: str, validation: ValidationResult, apply_changes: bool) -> list[RefactorPatch]:
        self.calls.append((apply_changes, repo_path))
        return [
            RefactorPatch(
                suggestion_id="suggestion-1",
                file_path=Path("app/foo.py"),
                original_chunk="return 1",
                patched_chunk="return helper()",
                status=RefactorStatus.VALIDATED,
            )
        ]


class _FakeMaterializeReviewBranch:
    def __init__(self) -> None:
        self.calls: list[tuple[bool, bool, str, str | None]] = []

    def execute(
        self,
        patches: list,
        repo_path: str,
        start_ref: str,
        validation: ValidationResult,
        enabled: bool,
        branch_name: str | None = None,
        push: bool = False,
        remote_name: str = "origin",
    ) -> ReviewBranchMaterialization | None:
        self.calls.append((enabled, push, start_ref, branch_name))
        if not enabled:
            return None
        return ReviewBranchMaterialization(
            branch_name=branch_name or "feature-refactor",
            commit_sha="abc123",
            pushed=push,
            remote_ref=f"{remote_name}/{branch_name or 'feature-refactor'}" if push else None,
            committed_files=("app/foo.py",),
        )


class _FakeValidateReviewBranch:
    def __init__(self, result: ValidationResult | None = None) -> None:
        self._result = result or ValidationResult.safe(executed_checks=["TEST:repo-wide -> pytest -q"])
        self.calls: list[tuple[bool, str | None, str]] = []

    def execute(self, review_branch, repo_path, profile, changed_files, enabled: bool):  # type: ignore[no-untyped-def]
        branch_name = review_branch.branch_name if review_branch is not None else None
        self.calls.append((enabled, branch_name, repo_path))
        if not enabled or review_branch is None:
            return None
        return self._result


class _FakeCreateReviewPullRequest:
    def __init__(self) -> None:
        self.calls: list[tuple[bool, str | None, str | None, str | None]] = []

    def execute(self, review_branch, repository, base_branch, enabled: bool):  # type: ignore[no-untyped-def]
        branch_name = review_branch.branch_name if review_branch is not None else None
        self.calls.append((enabled, repository, base_branch, branch_name))
        if not enabled or review_branch is None:
            return None
        return PullRequestPublication(
            number=99,
            url="https://github.com/acme/refactor-agent/pull/99",
            head_branch=review_branch.branch_name,
            base_branch=base_branch or "main",
            created=True,
        )


class _FakePublishPullRequestComment:
    def __init__(self) -> None:
        self.calls: list[tuple[bool, str | None, int | None]] = []

    def execute(self, result, repository, pull_request_number, enabled: bool):  # type: ignore[no-untyped-def]
        self.calls.append((enabled, repository, pull_request_number))
        if not enabled or pull_request_number is None:
            return None
        return PullRequestCommentPublication(
            comment_id=1234,
            url="https://github.com/acme/refactor-agent/pull/99#issuecomment-1234",
            updated=False,
        )


def _build_orchestrator(
    scope: CodeScope,
    materialize_patches: _FakeMaterializePatches | None = None,
    materialize_review_branch: _FakeMaterializeReviewBranch | None = None,
    validate_review_branch: _FakeValidateReviewBranch | None = None,
    create_review_pull_request: _FakeCreateReviewPullRequest | None = None,
    publish_pull_request_comment: _FakePublishPullRequestComment | None = None,
) -> RunEngineeringGovernanceAgentUseCase:
    review_flow = ReviewAutomationFlow(
        materialize_review_branch=materialize_review_branch or _FakeMaterializeReviewBranch(),  # type: ignore[arg-type]
        validate_review_branch=validate_review_branch or _FakeValidateReviewBranch(),  # type: ignore[arg-type]
        create_review_pull_request=create_review_pull_request or _FakeCreateReviewPullRequest(),  # type: ignore[arg-type]
        publish_pull_request_comment=publish_pull_request_comment or _FakePublishPullRequestComment(),  # type: ignore[arg-type]
    )
    return RunEngineeringGovernanceAgentUseCase(
        analyze_diff=_FakeAnalyzeDiff(scope),  # type: ignore[arg-type]
        detect_profile=_FakeDetectProfile(),  # type: ignore[arg-type]
        filter_scope=_FakeFilterScope(),  # type: ignore[arg-type]
        load_policies=_FakeLoadPolicies(),  # type: ignore[arg-type]
        build_context=_FakeBuildContext(),  # type: ignore[arg-type]
        generate_docs=_FakeGenerateDocs(),  # type: ignore[arg-type]
        generate_refactors=_FakeGenerateRefactors(),  # type: ignore[arg-type]
        validate_safety=_FakeValidateSafety(),  # type: ignore[arg-type]
        materialize_patches=materialize_patches or _FakeMaterializePatches(),  # type: ignore[arg-type]
        review_flow=review_flow,
        publish_report=_FakePublishReport(),  # type: ignore[arg-type]
    )


def _make_request(**overrides: object) -> AgentRunRequest:
    defaults: dict = {
        "repo_path": "/repo",
        "base_ref": "main",
        "head_ref": "feature",
        "run_id": "test-run",
        "triggered_by": "cli",
        "dry_run": True,
        "publish_review_branch": False,
        "push_review_branch": False,
        "validate_review_branch": False,
        "review_remote_name": "origin",
        "publish_pr_comment": False,
        "create_review_pull_request": False,
    }
    defaults.update(overrides)
    return AgentRunRequest(**defaults)  # type: ignore[arg-type]


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestRunEngineeringGovernanceAgentUseCase:
    def test_success_on_empty_scope(self) -> None:
        agent = _build_orchestrator(CodeScope(base_ref="main", head_ref="feature"))
        response = agent.run(_make_request())
        assert response.success is True
        assert response.error is None

    def test_success_with_changed_files(self) -> None:
        scope = CodeScope(
            changed_files=[
                ChangedFile(
                    path=Path("app/service.py"),
                    change_type=ChangeType.MODIFIED,
                    language=Language.PYTHON,
                    diff_content="",
                )
            ],
            base_ref="main",
            head_ref="feature",
        )
        agent = _build_orchestrator(scope)
        response = agent.run(_make_request(run_id="test-run-2"))
        assert response.success is True
        assert response.result is not None
        assert response.result.run_id == "test-run-2"

    def test_report_not_published_in_dry_run(self) -> None:
        scope = CodeScope(
            changed_files=[
                ChangedFile(
                    path=Path("app/foo.py"),
                    change_type=ChangeType.ADDED,
                    language=Language.PYTHON,
                    diff_content="",
                )
            ],
        )
        agent = _build_orchestrator(scope)
        response = agent.run(_make_request(dry_run=True))
        assert response.success is True
        # Report path must be None when dry_run=True
        assert response.result is not None
        assert response.result.report_path is None

    def test_report_is_published_when_not_dry_run(self) -> None:
        scope = CodeScope(
            changed_files=[
                ChangedFile(
                    path=Path("app/foo.py"),
                    change_type=ChangeType.ADDED,
                    language=Language.PYTHON,
                    diff_content="",
                )
            ],
        )
        agent = _build_orchestrator(scope)
        response = agent.run(_make_request(dry_run=False))

        assert response.success is True
        assert response.result is not None
        assert response.result.report_path == "/tmp/report.md"

    def test_returns_error_response_on_exception(self) -> None:
        class _BrokenAnalyzeDiff:
            def execute(self, *args: object, **kwargs: object) -> None:
                raise RuntimeError("Simulated failure")

        agent = RunEngineeringGovernanceAgentUseCase(
            analyze_diff=_BrokenAnalyzeDiff(),  # type: ignore[arg-type]
            detect_profile=_FakeDetectProfile(),  # type: ignore[arg-type]
            filter_scope=_FakeFilterScope(),  # type: ignore[arg-type]
            load_policies=_FakeLoadPolicies(),  # type: ignore[arg-type]
            build_context=_FakeBuildContext(),  # type: ignore[arg-type]
            generate_docs=_FakeGenerateDocs(),  # type: ignore[arg-type]
            generate_refactors=_FakeGenerateRefactors(),  # type: ignore[arg-type]
            validate_safety=_FakeValidateSafety(),  # type: ignore[arg-type]
            materialize_patches=_FakeMaterializePatches(),  # type: ignore[arg-type]
            review_flow=ReviewAutomationFlow(
                materialize_review_branch=_FakeMaterializeReviewBranch(),  # type: ignore[arg-type]
                validate_review_branch=_FakeValidateReviewBranch(),  # type: ignore[arg-type]
                create_review_pull_request=_FakeCreateReviewPullRequest(),  # type: ignore[arg-type]
                publish_pull_request_comment=_FakePublishPullRequestComment(),  # type: ignore[arg-type]
            ),
            publish_report=_FakePublishReport(),  # type: ignore[arg-type]
        )
        response = agent.run(_make_request())
        assert response.success is False
        assert "Simulated failure" in (response.error or "")

    def test_materializes_patch_previews_after_validation(self) -> None:
        scope = CodeScope(
            changed_files=[
                ChangedFile(
                    path=Path("app/foo.py"),
                    change_type=ChangeType.ADDED,
                    language=Language.PYTHON,
                    diff_content="",
                )
            ],
        )
        materialize_patches = _FakeMaterializePatches()
        agent = _build_orchestrator(scope, materialize_patches=materialize_patches)

        response = agent.run(_make_request(dry_run=False, apply_refactors=True))

        assert response.success is True
        assert materialize_patches.calls == [(True, "/repo")]
        assert response.result is not None
        assert response.result.refactor_patches[0].status == RefactorStatus.VALIDATED

    def test_materializes_review_branch_when_enabled(self) -> None:
        scope = CodeScope(
            changed_files=[
                ChangedFile(
                    path=Path("app/foo.py"),
                    change_type=ChangeType.ADDED,
                    language=Language.PYTHON,
                    diff_content="",
                )
            ],
        )
        materialize_review_branch = _FakeMaterializeReviewBranch()
        agent = _build_orchestrator(scope, materialize_review_branch=materialize_review_branch)

        response = agent.run(
            _make_request(
                dry_run=False,
                publish_review_branch=True,
                push_review_branch=True,
                review_branch_name="ticket123_refactor",
                head_ref="feature/ticket123",
            )
        )

        assert response.success is True
        assert materialize_review_branch.calls == [
            (True, True, "feature/ticket123", "ticket123_refactor")
        ]
        assert response.result is not None
        assert response.result.review_branch is not None
        assert response.result.review_branch.branch_name == "ticket123_refactor"

    def test_creates_review_pull_request_and_publishes_comment(self) -> None:
        scope = CodeScope(
            changed_files=[
                ChangedFile(
                    path=Path("app/foo.py"),
                    change_type=ChangeType.ADDED,
                    language=Language.PYTHON,
                    diff_content="",
                )
            ],
        )
        create_review_pull_request = _FakeCreateReviewPullRequest()
        validate_review_branch = _FakeValidateReviewBranch()
        publish_pull_request_comment = _FakePublishPullRequestComment()
        agent = _build_orchestrator(
            scope,
            validate_review_branch=validate_review_branch,
            create_review_pull_request=create_review_pull_request,
            publish_pull_request_comment=publish_pull_request_comment,
        )

        response = agent.run(
            _make_request(
                dry_run=False,
                repository="acme/refactor-agent",
                base_branch="main",
                publish_review_branch=True,
                validate_review_branch=True,
                create_review_pull_request=True,
                publish_pr_comment=True,
                review_branch_name="ticket123_refactor",
            )
        )

        assert response.success is True
        assert validate_review_branch.calls == [
            (True, "ticket123_refactor", "/repo")
        ]
        assert create_review_pull_request.calls == [
            (True, "acme/refactor-agent", "main", "ticket123_refactor")
        ]
        assert publish_pull_request_comment.calls == [
            (True, "acme/refactor-agent", 99)
        ]
        assert response.result is not None
        assert response.result.review_pull_request is not None
        assert response.result.pull_request_comment is not None

    def test_blocks_review_pull_request_when_review_branch_validation_fails(self) -> None:
        scope = CodeScope(
            changed_files=[
                ChangedFile(
                    path=Path("app/foo.py"),
                    change_type=ChangeType.ADDED,
                    language=Language.PYTHON,
                    diff_content="",
                )
            ],
        )
        validate_review_branch = _FakeValidateReviewBranch(
            ValidationResult.unsafe(summary="Generated branch validation failed.")
        )
        create_review_pull_request = _FakeCreateReviewPullRequest()
        agent = _build_orchestrator(
            scope,
            validate_review_branch=validate_review_branch,
            create_review_pull_request=create_review_pull_request,
        )

        response = agent.run(
            _make_request(
                dry_run=False,
                repository="acme/refactor-agent",
                base_branch="main",
                publish_review_branch=True,
                validate_review_branch=True,
                create_review_pull_request=True,
                review_branch_name="ticket123_refactor",
            )
        )

        assert response.success is True
        assert create_review_pull_request.calls == [
            (False, "acme/refactor-agent", "main", "ticket123_refactor")
        ]
        assert response.result is not None
        assert response.result.review_pull_request is None
        assert response.result.review_branch_validation_result is not None
        assert response.result.review_branch_validation_result.passed is False
