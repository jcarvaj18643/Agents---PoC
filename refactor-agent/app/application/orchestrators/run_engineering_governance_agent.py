from datetime import datetime, timezone

from app.application.dto.agent_run_request import AgentRunRequest
from app.application.dto.agent_run_response import AgentRunResponse
from app.application.ports.inbound.run_agent_port import RunAgentPort
from app.application.use_cases.analyze_diff_scope import AnalyzeDiffScopeUseCase
from app.application.use_cases.build_code_context import BuildCodeContextUseCase
from app.application.use_cases.detect_project_profile import DetectProjectProfileUseCase
from app.application.use_cases.filter_scope_by_profile import FilterScopeByProfileUseCase
from app.application.use_cases.generate_documentation import GenerateDocumentationUseCase
from app.application.use_cases.generate_refactor_suggestions import (
    GenerateRefactorSuggestionsUseCase,
)
from app.application.use_cases.create_review_pull_request import (
    CreateReviewPullRequestUseCase,
)
from app.application.use_cases.load_engineering_policies import LoadEngineeringPoliciesUseCase
from app.application.use_cases.materialize_refactor_patches import MaterializeRefactorPatchesUseCase
from app.application.use_cases.materialize_review_branch import (
    MaterializeReviewBranchUseCase,
)
from app.application.use_cases.publish_pull_request_comment import (
    PublishPullRequestCommentUseCase,
)
from app.application.use_cases.publish_agent_report import PublishAgentReportUseCase
from app.application.use_cases.validate_refactor_safety import ValidateRefactorSafetyUseCase
from app.domain.value_objects.agent_run_result import AgentRunResult


class RunEngineeringGovernanceAgentUseCase(RunAgentPort):
    """Top-level orchestrator use case (implements the inbound RunAgentPort).

    Sequences all specialised use cases in the correct order.
    This class owns *orchestration* only — no domain logic and no infrastructure
    concern lives here.

    Pipeline:
        1. Analyze diff scope
        2. Detect project profile
        3. Load engineering policies
        4. Build enriched code context
        5. Generate documentation artifacts
        6. Generate refactor suggestions
        7. Validate refactor safety
        8. Materialize patch previews and optional apply
        9. Publish report (skipped in dry-run mode)
    """

    def __init__(
        self,
        analyze_diff: AnalyzeDiffScopeUseCase,
        detect_profile: DetectProjectProfileUseCase,
        filter_scope: FilterScopeByProfileUseCase,
        load_policies: LoadEngineeringPoliciesUseCase,
        build_context: BuildCodeContextUseCase,
        generate_docs: GenerateDocumentationUseCase,
        generate_refactors: GenerateRefactorSuggestionsUseCase,
        validate_safety: ValidateRefactorSafetyUseCase,
        materialize_patches: MaterializeRefactorPatchesUseCase,
        materialize_review_branch: MaterializeReviewBranchUseCase,
        create_review_pull_request: CreateReviewPullRequestUseCase,
        publish_pull_request_comment: PublishPullRequestCommentUseCase,
        publish_report: PublishAgentReportUseCase,
    ) -> None:
        self._analyze_diff = analyze_diff
        self._detect_profile = detect_profile
        self._filter_scope = filter_scope
        self._load_policies = load_policies
        self._build_context = build_context
        self._generate_docs = generate_docs
        self._generate_refactors = generate_refactors
        self._validate_safety = validate_safety
        self._materialize_patches = materialize_patches
        self._materialize_review_branch = materialize_review_branch
        self._create_review_pull_request = create_review_pull_request
        self._publish_pull_request_comment = publish_pull_request_comment
        self._publish_report = publish_report

    def run(self, request: AgentRunRequest) -> AgentRunResponse:
        try:
            # 1. Analyze changed scope
            scope = self._analyze_diff.execute(
                request.base_ref, request.head_ref, request.repo_path
            )

            if scope.is_empty:
                result = AgentRunResult(
                    run_id=request.run_id,
                    success=True,
                    completed_at=datetime.now(timezone.utc),
                    changed_files=[],
                )
                return AgentRunResponse(success=True, result=result)

            # 2. Detect project profile
            profile = self._detect_profile.execute(request.repo_path)

            # 3. Restrict scope to files relevant to the detected stack
            scope = self._filter_scope.execute(scope, profile)
            if scope.is_empty:
                result = AgentRunResult(
                    run_id=request.run_id,
                    success=True,
                    completed_at=datetime.now(timezone.utc),
                    changed_files=[],
                    project_profile=profile,
                )
                return AgentRunResponse(success=True, result=result)

            # 4. Load applicable policies
            policies = self._load_policies.execute(profile.name)

            # 5. Build enriched code context
            files = self._build_context.execute(scope, request.repo_path)

            # 6. Generate documentation artifacts
            doc_artifacts = self._generate_docs.execute(files, policies)

            # 7. Generate refactor suggestions
            suggestions = self._generate_refactors.execute(files, policies)

            # 8. Validate safety of suggestions
            validation = self._validate_safety.execute(
                suggestions,
                files,
                request.repo_path,
                profile,
            )

            patches = self._materialize_patches.execute(
                suggestions,
                request.repo_path,
                validation,
                apply_changes=request.apply_refactors,
            )

            review_branch = self._materialize_review_branch.execute(
                patches,
                request.repo_path,
                request.head_ref,
                validation,
                enabled=request.publish_review_branch,
                branch_name=request.review_branch_name,
                push=request.push_review_branch,
                remote_name=request.review_remote_name,
            )

            review_pull_request = self._create_review_pull_request.execute(
                review_branch,
                request.repository,
                request.base_branch,
                enabled=request.create_review_pull_request,
            )

            # 9. Assemble result
            result = AgentRunResult(
                run_id=request.run_id,
                success=True,
                completed_at=datetime.now(timezone.utc),
                changed_files=files,
                project_profile=profile,
                applied_policies=policies,
                documentation_artifacts=doc_artifacts,
                refactor_suggestions=suggestions,
                refactor_patches=patches,
                review_branch=review_branch,
                review_pull_request=review_pull_request,
                llm_stage_modes={
                    "documentation": self._generate_docs.last_execution_mode,
                    "refactor": self._generate_refactors.last_execution_mode,
                },
                validation_result=validation,
            )

            # 10. Publish report (skipped in dry-run mode)
            if not request.dry_run:
                result.report_path = self._publish_report.execute(result)

            target_pull_request_number = request.pull_request_number
            if target_pull_request_number is None and result.review_pull_request is not None:
                target_pull_request_number = result.review_pull_request.number

            result.pull_request_comment = self._publish_pull_request_comment.execute(
                result,
                request.repository,
                target_pull_request_number,
                enabled=request.publish_pr_comment,
            )

            return AgentRunResponse(success=True, result=result)

        except Exception as exc:  # noqa: BLE001
            return AgentRunResponse(success=False, error=str(exc))
