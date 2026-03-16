Implementation Strategy

Build this in value-bearing layers, not technology layers. The correct sequence is: make scope truthful first, make project behavior deterministic second, make reporting useful third, then introduce LLMs, then safety gates, and only after that introduce write-capable behavior.

The key architectural rule is that the system must become useful before it becomes autonomous. In practice, that means the first end-to-end milestone is not "LLM suggestions," it is "a CI-safe, diff-scoped report that proves the agent only saw changed code and selected the right profile/policies." That gives you an auditable baseline before any probabilistic behavior enters the pipeline.

The implementation should preserve these boundaries throughout:
- Domain remains pure and owns only business concepts such as CodeScope, ProjectProfile, EngineeringPolicy, RefactorSuggestion, ValidationResult.
- Application owns sequencing, filtering, applicability rules, safety policy, and orchestration.
- Infrastructure owns git subprocess execution, filesystem access, YAML parsing, LLM API calls, GitHub runtime integration, and report publishing.
- Entrypoints stay thin and call the same inbound use case from both CLI and GitHub Actions.

Recommended rollout logic:
1. Make the diff scope real.
2. Make profile detection and policy loading real.
3. Make deterministic reporting useful with no LLM dependency.
4. Introduce documentation generation as the first LLM feature.
5. Introduce refactor suggestions as advisory only.
6. Add validation gates before any write capability.
7. Harden GitHub Actions and artifact visibility.
8. Add optional patch generation.
9. Add optional PR feedback and controlled apply workflows.

Phase-by-Phase Plan

1. Phase 0: Baseline Hardening and Walking Skeleton Confirmation
- Purpose: freeze the scaffold as a known-good baseline and remove ambiguity about what is placeholder versus functional.
- Why it belongs here: the scaffold already exists, so the first real step is to lock in behavior and prevent regressions before deeper implementation.
- Exact modules involved: app/bootstrap/container.py, app/application/orchestrators/run_engineering_governance_agent.py, app/entrypoints/cli/main.py, app/entrypoints/github_actions/runner.py, tests/unit/application/test_run_governance_agent.py.
- Expected outputs/artifacts: green baseline tests, explicit placeholder inventory, agreed dry-run semantics, agreed logging fields.
- Validation strategy: run the existing unit suite, verify empty-scope behavior, verify dry-run publishes nothing, verify entrypoints and container remain stable.
- Example of what should work: CLI and GitHub Actions runner both invoke the orchestrator cleanly and return success on an empty scope without side effects.
- What should NOT be attempted yet: parser implementation, policy schema, LLM integration, patch logic.

2. Phase 1: Real Diff Scope Analysis and Scope Governance
- Purpose: make CodeScope truthful and guarantee the agent only sees changed files.
- Why it belongs here: this is the blocking dependency for every downstream use case.
- Exact modules involved: app/infrastructure/parsers/diff_parser.py, app/infrastructure/adapters/git/git_diff_reader_adapter.py, app/application/use_cases/analyze_diff_scope.py, app/domain/entities/code_scope.py, app/domain/entities/changed_file.py, tests/fixtures/sample_diff.py, tests/unit/infrastructure/test_git_diff_reader_adapter.py.
- Expected outputs/artifacts: real ChangedFile objects, correct ChangeType, inferred Language, line counts, diff snippets per file, exclusion rules for generated/vendor paths.
- Validation strategy: parser unit tests for add/modify/delete/rename/multi-file cases, integration test against a temp git repo, explicit assertions that unchanged files never enter scope.
- Example of what should work: a diff between main and HEAD produces a non-empty CodeScope containing only touched files and accurate added/removed line counts.
- What should NOT be attempted yet: AST symbol extraction, prompt building, documentation generation, refactor generation.

3. Phase 2: Project Profile Detection and Policy Loading Foundation
- Purpose: make project-specific behavior deterministic through profile detection and YAML-based policies.
- Why it belongs here: once scope is real, the next business-critical concern is selecting the right rules for that repo.
- Exact modules involved: app/infrastructure/adapters/filesystem/project_structure_reader_adapter.py, app/application/use_cases/detect_project_profile.py, app/infrastructure/adapters/policy_loader/yaml_policy_loader_adapter.py, app/application/use_cases/load_engineering_policies.py, app/domain/value_objects/project_profile.py, app/domain/value_objects/engineering_policy.py.
- Expected outputs/artifacts: YAML schema for policies, sample profile policy files, deterministic ProjectProfile, parsed EngineeringPolicy objects, clear missing-policy warnings.
- Validation strategy: unit tests for marker-file heuristics, malformed-policy tests, contract tests for YAML parsing and merge order.
- Example of what should work: a Python repo is detected as Python, pytest can be inferred when relevant, and Python-specific policies are loaded into the orchestrator.
- What should NOT be attempted yet: LLM prompt templates, automatic policy repair, patch execution.

4. Phase 3: Scoped Context Building and First Useful Report
- Purpose: deliver the first genuinely useful output without relying on LLMs.
- Why it belongs here: this is the right "first value" milestone because it proves scope, profile, policy selection, and traceability in one run.
- Exact modules involved: app/application/use_cases/build_code_context.py, app/application/use_cases/publish_agent_report.py, app/infrastructure/adapters/filesystem/filesystem_adapter.py, app/infrastructure/adapters/reporting/markdown_report_publisher_adapter.py, app/domain/value_objects/agent_run_result.py.
- Expected outputs/artifacts: bounded file context for changed files only, markdown report listing changed files, profile, applied policies, skipped-file reasons, scope metrics.
- Validation strategy: report snapshot tests, integration test for report writing, manual run on a small diff, assertions that context never reads outside the repo root.
- Example of what should work: running the agent with no LLM configured still produces a useful markdown artifact showing exactly what changed and which rules would govern later phases.
- What should NOT be attempted yet: generated docs, LLM calls, PR comments, patch generation.

5. Phase 4: Documentation Generation MVP
- Purpose: introduce the first LLM dependency in the safest possible way.
- Why it belongs here: documentation generation is lower risk than refactoring and benefits directly from already-correct scope, profile, policies, and context.
- Exact modules involved: app/application/use_cases/generate_documentation.py, app/application/ports/outbound/llm_documentation_generator_port.py, app/infrastructure/adapters/llm/llm_documentation_generator_adapter.py, app/domain/entities/documentation_artifact.py, app/infrastructure/config/settings.py.
- Expected outputs/artifacts: policy-aware documentation prompts, token budgeting rules, generated DocumentationArtifact records, model/tokens metadata in the report.
- Validation strategy: mocked OpenAI client tests, prompt golden tests, response parsing tests, manual dry-run on a small PR.
- Example of what should work: the agent generates documentation text only for changed files and records which model and token budget were used.
- What should NOT be attempted yet: writing docs back into source files, refactor suggestions, patch generation.

6. Phase 5: Refactor Suggestion Generation, Advisory Only
- Purpose: produce refactor guidance without any write capability.
- Why it belongs here: once documentation generation and policy application are stable, refactor recommendations become the next value step, but they must remain non-executing.
- Exact modules involved: app/application/use_cases/generate_refactor_suggestions.py, app/application/ports/outbound/llm_refactor_advisor_port.py, app/infrastructure/adapters/llm/llm_refactor_advisor_adapter.py, app/domain/entities/refactor_suggestion.py, app/application/policies/refactor_safety_policy.py.
- Expected outputs/artifacts: structured suggestions with severity, rationale, rule reference, scoped file target, deduplication/ranking behavior.
- Validation strategy: structured-output contract tests, unit tests for filtering and deduplication, manual review on representative diffs.
- Example of what should work: the report contains advisory refactor suggestions for changed files only, with no filesystem changes.
- What should NOT be attempted yet: patch creation, patch application, CI-blocking safety gates.

7. Phase 6: Safety Assessment and Non-Intrusive Quality Gates
- Purpose: classify advisory suggestions with explicit safety policies and repo-aware validation planning without executing anything inside the target repo.
- Why it belongs here: safety assessment must exist before any write-capable behavior is even considered, but this phase must remain read-only over the target repository.
- Exact modules involved: app/application/use_cases/validate_refactor_safety.py, app/application/ports/outbound/validation_runner_port.py, app/application/policies/refactor_safety_policy.py, app/domain/value_objects/validation_result.py, app/domain/exceptions/domain_exceptions.py, plus a new infrastructure validation adapter.
- Expected outputs/artifacts: expanded safety rules, non-executing validation-plan adapter, explainable ValidationResult, clearer safe/unsafe/refused/skipped states, and explicit "recommended CI/CD checks" metadata.
- Validation strategy: negative tests proving policy violations block eligibility, contract tests proving the validation adapter returns plans instead of running commands, integration tests against temp repos for target-resolution only, and rule-level unit tests.
- Example of what should work: a suggestion may be present in the report but marked unsafe because it violates a policy, or marked pending because it requires CI/CD checks that are reported but not executed by the agent.
- What should NOT be attempted yet: applying changes to the target repo, running unit tests or lint commands inside the target repo, PR writes, automatic commits.

8. Phase 6.1: Diff-First Full-File Context and Change-Focused Refactor Reasoning
- Purpose: preserve diff-scoped activation while giving the agent enough file-level context to detect duplication, existing helpers, and local design opportunities.
- Why it belongs here: once safety states exist, the next quality gap is reasoning depth. Refactor guidance should stay anchored to changed files, but it should not be blind to the rest of each changed file.
- Exact modules involved: app/application/use_cases/build_code_context.py, app/domain/entities/changed_file.py, app/application/use_cases/generate_refactor_suggestions.py, app/infrastructure/adapters/llm/llm_refactor_advisor_adapter.py, app/infrastructure/adapters/reporting/markdown_report_publisher_adapter.py, and optionally symbol/reference retrieval adapters introduced behind new outbound ports.
- Expected outputs/artifacts: dual-context payloads per changed file (full-file context plus changed-hunk focus), change-anchored refactor rationale, explicit report traceability showing which suggestion was driven by which changed region.
- Validation strategy: unit tests for context assembly, regression tests proving unchanged files are not promoted into scope, prompt/heuristic tests ensuring suggestions cite the changed hunk while using full-file evidence, and representative manual reviews on duplicated-code diffs.
- Example of what should work: a changed file with repeated logic elsewhere in the same file yields a suggestion to extract or reuse an existing helper, and the report explains that the recommendation is motivated by the new change, not by unrelated legacy code alone.
- What should NOT be attempted yet: cross-repo refactors, opportunistic cleanup of unrelated files, or widening the writable surface beyond the files already in diff scope.

9. Phase 6.2: Symbol-Aware Structural Context and Class/Method-Level Traceability
- Purpose: move from file-text heuristics to structural reasoning so the agent can identify the impacted method, class, or module and anchor refactor advice to that symbol boundary.
- Why it belongs here: 6.1 gives enough file context to improve recommendations, but it still reasons over text. Before expanding write behavior or review UX, the agent should understand which symbol actually changed.
- Exact modules involved: app/application/use_cases/build_code_context.py, app/domain/entities/changed_file.py, app/domain/entities/refactor_suggestion.py, app/application/use_cases/generate_refactor_suggestions.py, app/application/ports/outbound/symbol_context_resolver_port.py, app/infrastructure/adapters/parser/python_symbol_context_resolver_adapter.py, app/infrastructure/adapters/parser/csharp_symbol_context_resolver_adapter.py, app/infrastructure/adapters/parser/typescript_symbol_context_resolver_adapter.py, and app/infrastructure/adapters/reporting/markdown_report_publisher_adapter.py.
- Expected outputs/artifacts: impacted-symbol metadata per changed file, method/class/module context snapshots, symbol-aware duplication evidence, report traceability from diff hunk to symbol to recommendation.
- Validation strategy: unit tests for symbol resolution by language, regression tests for nested classes/functions, diff-to-symbol mapping tests, and manual runs proving the agent cites the containing method or class instead of generic file-wide evidence.
- Example of what should work: a change inside a service method resolves the containing method and class, detects repeated mapping logic in sibling methods of that same class, and recommends extracting a helper with the report explicitly naming the impacted symbol.
- What should NOT be attempted yet: repository-wide semantic indexing, cross-file rename proposals, or broad cleanup suggestions detached from the changed symbol.

10. Phase 6.3: Impact-Targeted Validation Planning and Public API Guardrails
- Purpose: determine the smallest impacted validation target and report the exact checks that CI/CD should run, instead of executing repo commands from the agent.
- Why it belongs here: once symbol and module boundaries are known, validation planning can become both faster and more trustworthy by selecting the affected package, project, test target, or lint scope without turning this stage into an executor.
- Exact modules involved: app/application/use_cases/validate_refactor_safety.py, app/application/ports/outbound/validation_runner_port.py, app/application/ports/outbound/impact_target_resolver_port.py, app/application/policies/refactor_safety_policy.py, app/domain/value_objects/validation_result.py, app/infrastructure/adapters/validation/profile_validation_runner_adapter.py, plus new impact-target resolver adapters per stack.
- Expected outputs/artifacts: impacted-target resolution for Python/C#/Angular stacks, targeted lint/test command plans, explicit fallback-to-broader-validation planning, public API guard results, and coverage/lint threshold expectations tied to the impacted target.
- Validation strategy: unit tests for target resolution, integration tests proving impacted-target selection by changed path/symbol, negative tests for public API changes, and manual runs confirming the report emits the intended CI/CD command plan without invoking it.
- Example of what should work: a changed Python module resolves its nearest test target, a changed C# project resolves its owning .csproj and test project, and an Angular component resolves the most specific available lint/test scope, with all of that rendered into the report as recommended follow-up checks.
- What should NOT be attempted yet: auto-fixing lint violations, mutating public API automatically, executing validation commands against the target repo, or treating planned validation as proof that unrelated repository areas are healthy.

11. Phase 6.4: Report Correctness, Traceability, and Noise Reduction
- Purpose: fix the report defects identified in real runs so the artifact clearly separates analysis status from CI/CD execution, traces each suggestion to the right changed symbol, and reduces low-value noise.
- Why it belongs here: after 6.1 through 6.3, the next bottleneck is not more capability but better report fidelity. The report must be trustworthy before it can drive later automation or review workflows.
- Exact modules involved: app/domain/value_objects/agent_run_result.py, app/application/use_cases/build_code_context.py, app/application/use_cases/generate_refactor_suggestions.py, app/application/orchestrators/run_engineering_governance_agent.py, app/infrastructure/adapters/parser/heuristic_symbol_context_resolver_adapter.py, app/infrastructure/adapters/llm/llm_refactor_advisor_adapter.py, app/infrastructure/adapters/reporting/markdown_report_publisher_adapter.py, app/infrastructure/config/settings.py.
- Expected outputs/artifacts: separate execution-status versus governance-status reporting, explicit validation section states such as skipped/planned-for-ci, improved diff-to-symbol mapping using actual added lines, stronger suggestion anchors than placeholder labels, reduced cosmetic/test-noise suggestions, and tighter context sections with less duplication.
- Validation strategy: report snapshot tests, diff-to-symbol mapping regression tests, suggestion-filtering tests, traceability tests from changed hunk to impacted symbol to recommendation, and manual review of published reports from representative target repos.
- Example of what should work: a report can say the run executed successfully, validation was intentionally deferred to CI/CD, a suggestion is anchored to the actual changed test method instead of an earlier symbol in the file, and cosmetic suggestions are filtered out.
- What should NOT be attempted yet: mutating the target repo, promoting placeholder anchors into production output, or using report generation as a substitute for CI/CD execution.

12. Phase 7: GitHub Actions Real Integration and Artifact Visibility
- Purpose: make CI the primary operational path for the PoC.
- Why it belongs here: by this point the outputs are useful enough to deserve real PR workflow visibility.
- Exact modules involved: app/entrypoints/github_actions/runner.py, app/infrastructure/adapters/github/github_context_provider_adapter.py, app/infrastructure/adapters/reporting/markdown_report_publisher_adapter.py, .github/workflows/governance_agent.yml, app/infrastructure/logging/console_logger.py.
- Expected outputs/artifacts: stable workflow execution, uploaded reports, run metadata, better failure visibility, environment/config checks.
- Validation strategy: manual dispatch tests, PR branch smoke tests, missing-secret failure-path validation, artifact inspection.
- Example of what should work: every PR run uploads a report artifact and logs enough context to explain scope, profile, policy count, and failure points.
- What should NOT be attempted yet: posting comments, pushing commits, auto-apply in CI.

13. Phase 8: Patch Generation and Guarded Safe Apply
- Purpose: add optional write-capable behavior under strict gates.
- Why it belongs here: this is the first phase that can mutate code, so it must come only after validation and CI observability are proven.
- Exact modules involved: app/application/ports/outbound/refactor_executor_port.py, app/domain/entities/refactor_patch.py, app/domain/enums/refactor_status.py, app/application/use_cases/validate_refactor_safety.py, app/bootstrap/container.py, plus a new executor adapter.
- Expected outputs/artifacts: RefactorPatch generation, patch previews, guarded apply mode, explicit config switches, rollback/sandbox behavior.
- Validation strategy: sandbox temp-repo integration tests, rollback tests, strict assertions that no patch can touch files outside approved scope.
- Example of what should work: validated suggestions can be transformed into patch previews and optionally applied in a sandbox when explicitly enabled.
- What should NOT be attempted yet: automatic commit/push to a review branch, merge automation, PR review automation.

14. Phase 8.1: Controlled Review Branch Materialization
- Purpose: materialize approved refactor patches into a dedicated review branch so humans can inspect concrete code changes before PR creation.
- Why it belongs here: once patch generation and guarded apply exist, the next step is not direct PR automation but controlled packaging of those changes into a reviewable branch.
- Exact modules involved: app/application/ports/outbound/refactor_executor_port.py, app/application/ports/outbound/review_branch_publisher_port.py, app/application/use_cases/materialize_review_branch.py, app/domain/entities/refactor_patch.py, app/domain/value_objects/validation_result.py, app/bootstrap/container.py, plus a new git branch publisher adapter.
- Expected outputs/artifacts: deterministic review-branch naming such as `xxxx_refactor`, isolated apply-to-branch behavior, structured commit messages, push-to-remote support, and a published branch reference ready for human review.
- Validation strategy: temp-repo integration tests for branch creation, commit creation, push simulation/mocking, assertions that only approved patch files are included, and rollback tests when branch materialization fails mid-flight.
- Example of what should work: a validated patch set is applied to a newly created branch like `ticket123_refactor`, committed with a structured message, pushed to remote, and reported back as ready for PR review.
- What should NOT be attempted yet: automatic PR creation, automatic reviewer assignment, autonomous merge, or bypassing explicit branch naming and safety gates.

15. Phase 8.2: Branch Validation and Promotion Gate
- Purpose: re-run the target repository validation suite against the materialized review branch before allowing PR promotion.
- Why it belongs here: once a branch can be materialized and pushed, the next missing safety gate is proving that the generated code still passes the repo's real CI checks before the agent escalates it into a review PR.
- Exact modules involved: app/application/ports/outbound/validation_runner_port.py, app/application/ports/outbound/review_branch_publisher_port.py, app/application/use_cases/materialize_review_branch.py, app/application/use_cases/validate_refactor_safety.py, app/infrastructure/adapters/validation/profile_validation_runner_adapter.py, app/entrypoints/github_actions/runner.py, .github/workflows/governance_agent.yml, plus a promotion-oriented use case or workflow gate that binds branch publication to post-branch validation outcomes.
- Expected outputs/artifacts: explicit post-materialization validation status, targeted validation execution against the generated review branch, promotion/no-promotion decision data, CI-visible logs for branch validation, and a guarantee that PR creation is blocked when the generated branch fails required checks.
- Validation strategy: temp-repo integration tests that materialize a branch and execute validation commands in the generated worktree, negative-path tests proving failed validation blocks PR promotion, workflow smoke tests proving the branch-validation job runs only after branch publication, and contract tests for promotion gating semantics.
- Example of what should work: the agent materializes `ticket123_refactor`, pushes it, runs the impacted lint/test plan against that branch, and only marks the branch as eligible for PR creation when those checks pass.
- What should NOT be attempted yet: direct autonomous merge, bypassing required tests, or treating branch creation alone as sufficient proof that the refactor is safe to propose.

16. Phase 9: PR Comment Integration and Production Hardening
- Purpose: close the feedback loop by surfacing results directly in code review.
- Why it belongs here: review UX is important, but it should not arrive before core safety and correctness are established.
- Exact modules involved: app/infrastructure/adapters/github/github_context_provider_adapter.py, app/infrastructure/adapters/reporting/markdown_report_publisher_adapter.py, .github/workflows/governance_agent.yml, app/application/orchestrators/run_engineering_governance_agent.py, plus new GitHub comment/review publisher adapters.
- Expected outputs/artifacts: PR summary comments, optional review annotations, optional PR creation from the review branch, idempotent update behavior, suppression controls, telemetry and retry/backoff hardening.
- Validation strategy: mocked GitHub API contract tests, manual tests on non-critical PRs, operational runbooks for failure scenarios.
- Example of what should work: the system can either comment on an existing PR or create a PR from the previously published review branch, then add a scoped summary comment with links to the artifact and clear status of docs, suggestions, and validation.
- What should NOT be attempted yet: autonomous merge or autonomous branch selection without explicit policy/configuration.

17. Phase 10: Agent Cutoff for Repository Move
- Purpose: declare the agent operationally ready to move from its development repository into the target repository where it will run in production.
- Why it belongs here: once Phase 8.2 makes branch validation a mandatory promotion gate, the remaining work is no longer about deciding whether the refactor is safe, but about embedding the agent into the destination repository's CI/CD topology, dependency model, permissions, and operational ownership.
- Exact modules involved: .github/workflows/governance_agent.yml, app/entrypoints/github_actions/runner.py, app/entrypoints/cli/main.py, app/infrastructure/config/settings.py, README.md, .env.example, plus the destination repository workflow that should invoke the agent after its existing unit-test workflow passes.
- Expected outputs/artifacts: a destination-repo installation checklist, an agent-specific dependency installation path, repo-local workflow wiring in the target repository, a post-unit-tests job topology where the agent runs only after the repository test suite succeeds, documented required secrets/permissions, and a cutoff checklist certifying that review-branch validation is the mandatory gate before PR creation.
- Validation strategy: manual dry-run and non-dry-run smoke tests inside the target repository, workflow_dispatch verification in the target repository, a full `unit-tests -> governance-agent -> branch-validation -> PR/comment` rehearsal in the target repo, PR comment idempotency verification from the target repository context, and proof that the agent can install its own dependencies without breaking the host repository environment.
- Example of what should work: the agent codebase is embedded in `rag_system`, its own dependencies are installed in CI, the existing `unit-tests` workflow/job passes first, the agent then runs on the same checkout, materializes and validates a review branch, and only after that gate passes does it create or reuse a PR and publish the summary comment.
- What should NOT be attempted yet: multi-repo distribution packaging, marketplace publication, bypassing the target repository's own test workflow, or allowing PR creation without the Phase 8.2 branch-validation gate.

Detailed Deliverables Per Phase

- Phase 0 delivers a locked baseline: green unit tests, placeholder inventory, agreed dry-run and logging semantics.
- Phase 1 delivers truthful CodeScope creation: real diff parsing, real git adapter execution, path exclusion rules, parser fixtures, temp-repo integration tests.
- Phase 2 delivers deterministic behavior selection: profile heuristics, YAML policy schema, sample policies, policy parser, merge order, missing-policy failure/warning behavior.
- Phase 3 delivers the first useful artifact: scoped code context, deterministic markdown report, run metadata, skipped-file traceability.
- Phase 4 delivers the first LLM feature: documentation prompt construction, bounded context usage, model invocation, artifact parsing, usage metadata.
- Phase 5 delivers advisory refactor intelligence: structured suggestions, ranking, deduplication, policy linkage, no side effects.
- Phase 6 delivers safety maturity: validation planning, richer safety policy rules, explainable validation outcomes, and CI/CD handoff data without executing target-repo commands.
- Phase 6.1 delivers deeper reasoning without scope drift: full-file context for changed files, changed-hunk anchoring, and refactor suggestions that can detect repetition or missed abstractions inside the changed file while remaining diff-triggered.
- Phase 6.2 delivers structural traceability: impacted-symbol resolution, method/class-level context, and symbol-aware recommendation evidence tied to the changed region.
- Phase 6.3 delivers impacted validation planning: smallest-target CI/CD checks, public API guardrails, and explicit fallback plans without agent-side execution.
- Phase 6.4 delivers report trustworthiness: separate statuses, stronger traceability, lower-noise suggestions, and cleaner validation semantics.
- Phase 7 delivers operational CI value: hardened GitHub workflow, artifact-first visibility, better logs and failure surfaces.
- Phase 8 delivers guarded mutation capability: patch generation, preview mode, apply toggle, sandbox execution and rollback tests.
- Phase 8.1 delivers controlled review packaging: branch creation, commit/push orchestration, and review-ready branch publication under strict gates.
- Phase 8.2 delivers promotion safety: post-branch validation execution, promotion gating, and explicit evidence that generated refactor branches pass the required checks before PR creation.
- Phase 9 delivers review-loop integration: PR comments, annotations, idempotent updates, operational hardening.
- Phase 10 delivers move readiness: cutoff checklist, target-repo installation path, repository-local workflow validation, post-unit-tests agent orchestration, and removal of source-repo coupling.

Dependency Graph Between Phases

1. Phase 0 is the baseline and must stay green throughout.
2. Phase 1 blocks everything else.
3. Phase 2 depends on Phase 1 for realistic repo inputs, though policy schema design can begin in parallel.
4. Phase 3 depends on Phases 1 and 2.
5. Phase 4 depends on Phases 1, 2, and 3.
6. Phase 5 depends on Phases 1, 2, and 3, and should follow Phase 4 so LLM infrastructure is introduced once.
7. Phase 6 depends on Phase 5.
8. Phase 6.1 depends on Phases 5 and 6.
9. Phase 6.3 depends on Phases 6, 6.1, and 6.2.
10. Phase 6.4 depends on Phases 6.1, 6.2, and 6.3.
11. Phase 7 depends on Phases 3 through 6.4 being stable enough to run in CI.
12. Phase 8 depends on Phases 6 and 6.4 being complete.
13. Phase 8.1 depends on Phases 7 and 8.
14. Phase 8.2 depends on Phase 8.1 and on validation execution being permitted for the generated branch context.
15. Phase 9 depends on Phase 7, and on Phase 8.2 if PR creation should be gated by successful branch validation.
16. Phase 10 depends on Phase 8.2 and Phase 9 and requires at least one successful end-to-end smoke test against the real target repository context with the agent running after the destination repository's own unit-test gate.

Safe parallelism:
1. Policy schema design can overlap with Phase 1 implementation.
2. Report formatting can begin during Phase 3 while documentation LLM work is being prepared.
3. GitHub Actions hardening can overlap late Phase 6 and Phase 7.

Acceptance Criteria Per Phase

- Phase 0: unit suite green, placeholders explicitly documented, dry-run proven side-effect-free.
- Phase 1: CodeScope contains only changed files, line counts are accurate, exclusions are enforced.
- Phase 2: supported repos yield deterministic ProjectProfile, valid YAML policies load cleanly, invalid YAML fails loudly.
- Phase 3: no-LLM runs still produce a useful report, report includes scope/profile/policies/skipped items, context building is repo-bounded.
- Phase 4: documentation artifacts are generated only for scoped files, failures are isolated and traceable, token/model metadata is recorded.
- Phase 5: refactor suggestions are structured and scoped, duplicates are filtered, no source files are modified.
- Phase 6: failed policy checks block eligibility, reports explain safety outcomes, and any validation commands are emitted as CI/CD plans rather than executed against the target repo.
- Phase 6.1: the agent reads the full contents of changed files while keeping activation anchored to diff scope, reports distinguish full-file evidence from changed-hunk evidence, and suggestions remain motivated by new changes rather than unrelated legacy areas.
- Phase 6.2: impacted symbols resolve to the actual changed method, class, or module, and reports show symbol-level evidence instead of generic file-wide attribution.
- Phase 6.3: impacted-target validation plans are specific, reproducible, and clearly marked as deferred to CI/CD execution.
- Phase 6.4: reports separate run success from governance outcome, impacted symbols map to the actual changed region, placeholder anchors are eliminated, and low-value suggestion noise is materially reduced.
- Phase 7: GitHub Actions runs reliably on PRs, artifacts upload consistently, missing configuration fails clearly.
- Phase 8: patch previews are accurate, apply mode is opt-in, no patch touches files outside approved scope.
- Phase 8.1: review branches are created deterministically, commits contain only approved refactor patches, pushes are explicit and auditable, and the resulting branch is ready for PR review.
- Phase 8.2: generated review branches are revalidated with the intended impacted checks, failed validation blocks PR promotion, and successful validation is visible as explicit promotion evidence.
- Phase 9: PR comments are idempotent or updateable, review visibility is sufficient, failures degrade safely.
- Phase 10: the agent runs inside the target repository without source-repo-specific configuration, installs its own dependencies without destabilizing the host CI, executes only after the destination repository unit-test gate passes, uses Phase 8.2 as the mandatory PR-promotion gate, and has a cutoff checklist explicitly marking it ready to move.

Technical Risks and Mitigations

- Silent empty-scope success.
  - Mitigation: parser-heavy test coverage, temp-repo integration tests, explicit zero-scope reason logging.

- Policy schema drift.
  - Mitigation: define schema and samples before parser logic; enforce contract tests.

- LLM token overrun or prompt bloat.
  - Mitigation: bounded context builder, prompt builders, token budgeting before full rollout.

- Business logic leaking into adapters.
  - Mitigation: keep applicability filtering, safety rules, ranking, and orchestration in application/domain only.

- Unsafe automation.
  - Mitigation: separate suggestion generation, validation, patch generation, and apply into distinct phases and ports.

- Weak CI diagnosability.
  - Mitigation: artifact-first reporting, structured logs, clearer exception taxonomy, always-upload behavior when possible.

- Overfitting to Python.
  - Mitigation: keep Language and ProjectProfile generic, encode language-specific behavior in policies and heuristics rather than core orchestration.

Suggested Development Order by File/Module

1. First wave:
   app/infrastructure/parsers/diff_parser.py
   app/infrastructure/adapters/git/git_diff_reader_adapter.py
   app/application/use_cases/analyze_diff_scope.py
   tests/fixtures/sample_diff.py
   tests/unit/infrastructure/test_git_diff_reader_adapter.py

2. Second wave:
   app/infrastructure/adapters/filesystem/project_structure_reader_adapter.py
   app/application/use_cases/detect_project_profile.py
   app/infrastructure/adapters/policy_loader/yaml_policy_loader_adapter.py
   sample policy files in a new policies/ directory

3. Third wave:
   app/application/use_cases/build_code_context.py
   app/infrastructure/adapters/reporting/markdown_report_publisher_adapter.py
   app/application/use_cases/publish_agent_report.py

4. Fourth wave:
   app/infrastructure/adapters/llm/llm_documentation_generator_adapter.py
   app/application/use_cases/generate_documentation.py

5. Fifth wave:
   app/infrastructure/adapters/llm/llm_refactor_advisor_adapter.py
   app/application/use_cases/generate_refactor_suggestions.py
   app/application/policies/refactor_safety_policy.py

6. Sixth wave:
   a new validation runner adapter
   app/application/use_cases/validate_refactor_safety.py
   app/bootstrap/container.py

7. Sixth-wave extension:
  app/application/use_cases/build_code_context.py
  app/domain/entities/changed_file.py
  app/application/use_cases/generate_refactor_suggestions.py
  optional symbol/reference retrieval ports and adapters

8. Seventh wave:
   .github/workflows/governance_agent.yml
   app/entrypoints/github_actions/runner.py
   app/infrastructure/adapters/github/github_context_provider_adapter.py

9. Eighth wave:
   a new refactor executor adapter
   app/application/ports/outbound/refactor_executor_port.py
   app/domain/entities/refactor_patch.py

10. Ninth wave:
   a new GitHub comment/review adapter
   reporting and workflow hardening modules

Definition of MVP, V1, and V2

- MVP:
  real diff scope parsing, real profile detection, real policy loading, bounded context building, useful markdown report in CLI and CI, no required LLM dependency.

- V1:
  everything in MVP, plus documentation generation via LLM, advisory refactor suggestions, safety validation gates, stable GitHub Actions artifact publishing.

- V2:
  everything in V1, plus optional patch generation, optional safe apply behind strict controls, PR comments and stronger operational telemetry.

- V3:
  everything in V2, plus branch-promotion validation, repository-move readiness, target-repo workflow installation after the host test gate, and a formal cutoff gate for production relocation.

Recommended Testing Strategy by Phase

- Phase 0: keep unit tests fast and hermetic around orchestrator, dry-run, and container wiring.
- Phase 1: heavy parser unit tests and temp-repo integration tests.
- Phase 2: heuristic tests for profile detection and YAML contract tests.
- Phase 3: integration tests for context building and markdown snapshots.
- Phase 4: mocked LLM client tests, prompt golden tests, response parsing tests, limited manual dry-runs.
- Phase 5: structured-output tests, ranking/dedup tests, report integration tests.
- Phase 6: isolated safety-assessment tests; negative-path tests are mandatory, and validation adapters must be proven non-executing against the target repo.
- Phase 6.1: dual-context assembly tests, changed-hunk anchoring tests, duplication-detection regression tests within changed files, and manual review of representative refactor suggestions where the file-level context matters.
- Phase 6.2: symbol-resolution tests by language, nested-symbol regression tests, and report assertions proving hunk-to-symbol traceability.
- Phase 6.3: impacted-target planning tests, public API guard tests, and report assertions for deferred CI/CD command plans.
- Phase 6.4: report snapshot tests, symbol-traceability regressions, suggestion-noise filtering tests, and manual review of published reports.
- Phase 7: workflow smoke tests through manual dispatch and branch PRs.
- Phase 8: sandbox patch application tests, rollback tests, scope-leak prevention tests.
- Phase 8.1: temp-repo branch/push integration tests, commit-content assertions, remote-publish mocks, and failure recovery tests.
- Phase 8.2: generated-branch validation tests, promotion-blocking negative tests, workflow-gate tests for sequential branch-then-validate execution, and manual smoke tests on non-critical generated branches.
- Phase 9: GitHub API mock tests, idempotency tests, PR-creation contract tests, and operational smoke tests.
- Phase 10: target-repo installation smoke tests, workflow-permission verification, dependency-isolation checks, post-unit-tests workflow sequencing tests, config portability checks, and at least one end-to-end run executed from the destination repository.

Cross-phase rule:
- Domain and application tests should remain hermetic.
- Infrastructure tests may touch filesystem and subprocess.
- External network calls should remain mocked unless explicitly running controlled manual verification.

What should remain mocked until later

- Live OpenAI calls should remain mocked until Phase 4 prompt contracts and bounded context are stable.
- Git branch creation, commit, and push should remain mocked until Phase 8.1.
- GitHub write APIs should remain mocked until Phase 9.
- Patch execution should remain mocked until Phase 8.
- Validation runner behavior can stay stubbed through Phase 5 while suggestion structure matures, and from Phase 6 onward it should remain read-only unless a later write-capable phase explicitly enables execution.
- Symbol-level or AST extraction can remain absent until after Phase 3 unless context precision requires it earlier.
- Retry/backoff/telemetry backends can remain mocked until CI behavior stabilizes.

Next coding phase recommendation

- Start with Phase 1.
- Rationale: the current orchestrator, CI runner, and reporting flow exist, but the system still produces empty scopes because app/infrastructure/parsers/diff_parser.py and app/infrastructure/adapters/git/git_diff_reader_adapter.py are placeholders. Implementing them first unlocks every downstream phase and creates the first truthful runtime behavior.
- First modules to implement:
  - app/infrastructure/parsers/diff_parser.py
  - app/infrastructure/adapters/git/git_diff_reader_adapter.py
  - app/application/use_cases/analyze_diff_scope.py
  - tests/fixtures/sample_diff.py
  - tests/unit/infrastructure/test_git_diff_reader_adapter.py
  - new integration test for temp git repo diff reading
- Target outcome for the first sprint: a CLI run against a repo with real changes yields a non-empty CodeScope and a deterministic report listing only changed files.

Recommended First Coding Sprint

- Implement Phase 1 only.
- Sprint scope:
  - Real unified diff parsing for add/modify/delete/rename.
  - Real git subprocess execution in the git adapter.
  - Scope exclusion rules in AnalyzeDiffScopeUseCase.
  - Parser fixtures and integration tests.
  - Minimal logging improvements for empty-scope reasons.
- Explicitly exclude from this sprint:
  - YAML policy parsing.
  - LLM adapters.
  - GitHub write APIs.
  - Patch generation or apply logic.

Execution Checklist

1. Lock the current baseline tests and document placeholders.
2. Expand diff fixtures for add/modify/delete/rename/multi-file/generated-file coverage.
3. Implement unified diff parsing into ChangedFile objects.
4. Implement git subprocess diff reading with error translation.
5. Add scope exclusion rules and skipped-path logging.
6. Add temp-repo integration tests for real scope acquisition.
7. Implement stronger project profile heuristics.
8. Define YAML policy schema and sample policy packs.
9. Implement policy parsing, validation, and deterministic merge behavior.
10. Implement bounded code context building for changed files only.
11. Upgrade report publishing to include scope/profile/policy/context data.
12. Add documentation prompt building and mocked LLM contract tests.
13. Implement documentation generation and artifact reporting.
14. Add refactor prompt building, parsing, ranking, and deduplication.
15. Expand safety policy rules and introduce the non-executing validation-plan adapter.
16. Implement Phase 6.4 report fixes: status separation, CI/CD-deferred validation semantics, improved symbol mapping, stronger anchors, and suggestion-noise filtering.
17. Harden GitHub Actions workflow behavior and artifact visibility.
18. Implement patch generation and guarded apply mode in sandbox tests.
19. Implement controlled review-branch creation, commit, and push for approved refactors.
20. Add PR creation/comment publication and production hardening controls.
