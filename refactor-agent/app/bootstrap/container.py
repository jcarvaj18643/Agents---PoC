"""Composition root (Dependency Injection container).

Wires every port to its concrete adapter, every use case to its dependencies,
and the orchestrator to all use cases. Nothing outside this module should
instantiate infrastructure classes directly.

This is intentionally explicit (no magic DI framework) so the dependency
graph is readable, traceable, and easy to swap during testing.
"""

from dataclasses import dataclass
from pathlib import Path

from app.application.orchestrators.run_engineering_governance_agent import (
    RunEngineeringGovernanceAgentUseCase,
)
from app.application.policies.refactor_safety_policy import RefactorSafetyPolicy
from app.application.use_cases.analyze_diff_scope import AnalyzeDiffScopeUseCase
from app.application.use_cases.build_code_context import BuildCodeContextUseCase
from app.application.use_cases.create_review_pull_request import (
    CreateReviewPullRequestUseCase,
)
from app.application.use_cases.detect_project_profile import DetectProjectProfileUseCase
from app.application.use_cases.filter_scope_by_profile import FilterScopeByProfileUseCase
from app.application.use_cases.generate_documentation import GenerateDocumentationUseCase
from app.application.use_cases.generate_refactor_suggestions import (
    GenerateRefactorSuggestionsUseCase,
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
from app.infrastructure.adapters.filesystem.filesystem_adapter import FileSystemAdapter
from app.infrastructure.adapters.filesystem.project_structure_reader_adapter import (
    ProjectStructureReaderAdapter,
)
from app.infrastructure.adapters.git.git_diff_reader_adapter import GitDiffReaderAdapter
from app.infrastructure.adapters.git.review_branch_publisher_adapter import (
    GitReviewBranchPublisherAdapter,
)
from app.infrastructure.adapters.github.github_context_provider_adapter import (
    GitHubContextProviderAdapter,
)
from app.infrastructure.adapters.github.github_pull_request_comment_publisher_adapter import (
    GitHubPullRequestCommentPublisherAdapter,
)
from app.infrastructure.adapters.github.github_pull_request_publisher_adapter import (
    GitHubPullRequestPublisherAdapter,
)
from app.infrastructure.adapters.llm.llm_documentation_generator_adapter import (
    LlmDocumentationGeneratorAdapter,
)
from app.infrastructure.adapters.llm.llm_refactor_advisor_adapter import (
    LlmRefactorAdvisorAdapter,
)
from app.infrastructure.adapters.policy_loader.yaml_policy_loader_adapter import (
    YamlPolicyLoaderAdapter,
)
from app.infrastructure.adapters.parser.heuristic_symbol_context_resolver_adapter import (
    HeuristicSymbolContextResolverAdapter,
)
from app.infrastructure.adapters.refactor.filesystem_refactor_executor_adapter import (
    FileSystemRefactorExecutorAdapter,
)
from app.infrastructure.adapters.reporting.markdown_report_publisher_adapter import (
    MarkdownReportPublisherAdapter,
)
from app.infrastructure.adapters.validation.profile_validation_runner_adapter import (
    ProfileValidationRunnerAdapter,
)
from app.infrastructure.adapters.validation.profile_impact_target_resolver_adapter import (
    ProfileImpactTargetResolverAdapter,
)
from app.infrastructure.config.settings import Settings
from app.infrastructure.parsers.diff_parser import DiffParser


@dataclass
class Container:
    """Holds all fully-wired top-level objects.

    Entrypoints receive this container and interact only with
    `governance_agent` (the inbound port) and `github_context_provider`
    (needed to read CI context). All other objects are internal.
    """

    governance_agent: RunEngineeringGovernanceAgentUseCase
    github_context_provider: GitHubContextProviderAdapter


def build_container() -> Container:
    """Build and return the fully wired dependency container.

    Call once at startup; the returned Container is effectively a singleton
    for the lifetime of a process.
    """
    settings = Settings.from_env()
    project_root = Path(__file__).resolve().parents[2]
    policies_dir = (
        settings.policies_dir
        if settings.policies_dir.is_absolute()
        else project_root / settings.policies_dir
    )
    reports_dir = (
        settings.reports_dir
        if settings.reports_dir.is_absolute()
        else project_root / settings.reports_dir
    )

    # ── Infrastructure ────────────────────────────────────────────────────────
    diff_parser = DiffParser()
    git_diff_reader = GitDiffReaderAdapter(diff_parser=diff_parser)
    filesystem = FileSystemAdapter()
    project_structure_reader = ProjectStructureReaderAdapter()
    llm_doc_generator = LlmDocumentationGeneratorAdapter(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
    )
    llm_refactor_advisor = LlmRefactorAdvisorAdapter(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
    )
    github_context_provider = GitHubContextProviderAdapter()
    policy_loader = YamlPolicyLoaderAdapter(policies_dir=policies_dir)
    report_publisher = MarkdownReportPublisherAdapter(output_dir=reports_dir)
    symbol_context_resolver = HeuristicSymbolContextResolverAdapter()
    refactor_executor = FileSystemRefactorExecutorAdapter()
    review_branch_publisher = GitReviewBranchPublisherAdapter(
        refactor_executor=refactor_executor,
    )
    pull_request_publisher = GitHubPullRequestPublisherAdapter(
        github_token=settings.github_token or "",
        api_base_url=settings.github_api_base_url,
    )
    pull_request_comment_publisher = GitHubPullRequestCommentPublisherAdapter(
        github_token=settings.github_token or "",
        api_base_url=settings.github_api_base_url,
    )

    # ── Policies ─────────────────────────────────────────────────────────────
    safety_policy = RefactorSafetyPolicy(
        max_suggestions_per_run=settings.max_suggestions_per_run,
        enforce_public_api_guard=settings.enforce_public_api_guard,
    )
    impact_target_resolver = ProfileImpactTargetResolverAdapter()

    validation_runner = ProfileValidationRunnerAdapter(
        lint_enabled=settings.enable_lint_validation,
        coverage_enabled=settings.enable_coverage_validation,
        execution_enabled=settings.execute_validation_checks,
        python_coverage_fail_under=settings.python_coverage_fail_under,
        impact_target_resolver=impact_target_resolver,
    )

    # ── Use Cases ─────────────────────────────────────────────────────────────
    analyze_diff = AnalyzeDiffScopeUseCase(diff_reader=git_diff_reader)
    detect_profile = DetectProjectProfileUseCase(structure_reader=project_structure_reader)
    filter_scope = FilterScopeByProfileUseCase()
    load_policies = LoadEngineeringPoliciesUseCase(policy_repository=policy_loader)
    build_context = BuildCodeContextUseCase(
        filesystem=filesystem,
        symbol_context_resolver=symbol_context_resolver,
    )
    generate_docs = GenerateDocumentationUseCase(llm_doc_generator=llm_doc_generator)
    generate_refactors = GenerateRefactorSuggestionsUseCase(
        llm_refactor_advisor=llm_refactor_advisor
    )
    validate_safety = ValidateRefactorSafetyUseCase(
        safety_policy=safety_policy,
        validation_runner=validation_runner,
    )
    materialize_patches = MaterializeRefactorPatchesUseCase(
        refactor_executor=refactor_executor,
    )
    materialize_review_branch = MaterializeReviewBranchUseCase(
        review_branch_publisher=review_branch_publisher,
    )
    create_review_pull_request = CreateReviewPullRequestUseCase(
        pull_request_publisher=pull_request_publisher,
    )
    publish_pull_request_comment = PublishPullRequestCommentUseCase(
        pull_request_comment_publisher=pull_request_comment_publisher,
    )
    publish_report = PublishAgentReportUseCase(report_publisher=report_publisher)

    # ── Orchestrator ──────────────────────────────────────────────────────────
    governance_agent = RunEngineeringGovernanceAgentUseCase(
        analyze_diff=analyze_diff,
        detect_profile=detect_profile,
        filter_scope=filter_scope,
        load_policies=load_policies,
        build_context=build_context,
        generate_docs=generate_docs,
        generate_refactors=generate_refactors,
        validate_safety=validate_safety,
        materialize_patches=materialize_patches,
        materialize_review_branch=materialize_review_branch,
        create_review_pull_request=create_review_pull_request,
        publish_pull_request_comment=publish_pull_request_comment,
        publish_report=publish_report,
    )

    return Container(
        governance_agent=governance_agent,
        github_context_provider=github_context_provider,
    )
