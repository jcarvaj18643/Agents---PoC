# Engineering Governance Agent

An AI-powered agent that documents code and proposes (or applies) refactors based on
engineering guidelines — scoped strictly to the changes introduced by a pull request
and triggered automatically via GitHub Actions.

---

## Purpose

The **Engineering Governance Agent** inspects only the code changed by a git diff,
applies project-specific documentation and refactoring policies, and produces:

- **Documentation artifacts** — auto-generated docstrings / module docs per changed file
- **Refactor suggestions** — LLM-driven proposals mapped to engineering policies
- **Validation results** — safety gate checks before any code modification
- **Markdown reports** — published as CI artifacts or PR comments

---

## Architecture

The project follows **Hexagonal Architecture (Ports and Adapters)** with strict
SOLID principles. Dependency direction always points inward:

```
entrypoints / bootstrap
      │
      ▼
 application  ◄───────────────────────────  infrastructure
 (use cases,      ports/adapters boundary    (git, LLM, FS,
  policies,                                   GitHub, YAML)
  orchestrator)
      │
      ▼
   domain
 (entities, value
  objects, enums,
  services)
```

See the [Architecture Summary](#architecture-summary) section for full details.

---

## Project Structure

```
refactor-agent/
├── app/
│   ├── domain/               # Pure business rules — no framework deps
│   │   ├── entities/
│   │   ├── value_objects/
│   │   ├── enums/
│   │   ├── services/
│   │   └── exceptions/
│   ├── application/          # Use cases, ports, policies, orchestrator
│   │   ├── ports/
│   │   │   ├── inbound/      # RunAgentPort
│   │   │   └── outbound/     # 9 outbound ports (Git, LLM, FS, GitHub, …)
│   │   ├── use_cases/        # 8 focused use cases
│   │   ├── policies/         # RefactorSafetyPolicy
│   │   ├── orchestrators/    # RunEngineeringGovernanceAgentUseCase
│   │   ├── dto/
│   │   ├── commands/
│   │   └── queries/
│   ├── infrastructure/       # Concrete adapters and config
│   │   ├── config/
│   │   ├── logging/
│   │   ├── adapters/
│   │   │   ├── git/
│   │   │   ├── filesystem/
│   │   │   ├── llm/
│   │   │   ├── github/
│   │   │   ├── policy_loader/
│   │   │   └── reporting/
│   │   └── parsers/
│   ├── entrypoints/
│   │   ├── cli/              # Local CLI runner
│   │   └── github_actions/   # CI entrypoint
│   └── bootstrap/
│       └── container.py      # Composition root / DI wiring
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── .github/
│   └── workflows/
│       └── governance_agent.yml
├── pyproject.toml
├── requirements.txt
└── .env.example
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- An OpenAI API key (or compatible LLM endpoint)
- `git` available on `PATH`

### Setup

```bash
# Clone the repo and enter the project directory
cd refactor-agent

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy example env
cp .env.example .env
# Edit .env and fill in OPENAI_API_KEY
```

### Run locally

```bash
python -m app.entrypoints.cli.main \
    --repo-path /path/to/your/repo \
    --base-ref main \
    --head-ref HEAD \
    --dry-run

# Compare the latest branch commit against local uncommitted changes
python -m app.entrypoints.cli.main \
   --repo-path /path/to/your/repo \
   --base-ref HEAD \
   --head-ref WORKTREE \
   --dry-run
```

### Run tests

```bash
pip install -e ".[dev]"
pytest
```

### Code quality

```bash
black app tests
ruff check app tests
mypy app
```

---

## Configuration

All settings are read from environment variables (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | LLM API key |
| `LLM_MODEL` | `gpt-4o` | Model identifier |
| `DRY_RUN` | `true` | Skip report publishing and patch application |
| `MAX_SUGGESTIONS_PER_RUN` | `10` | Safety cap on refactor suggestions |
| `ENFORCE_PUBLIC_API_GUARD` | `true` | Refuse apply-eligibility when changed scope touches public API surfaces |
| `ENABLE_LINT_VALIDATION` | `true` | Run lint validation gates where supported |
| `ENABLE_COVERAGE_VALIDATION` | `true` | Run coverage validation gates where supported |
| `PYTHON_COVERAGE_FAIL_UNDER` | `80` | Minimum Python coverage threshold when coverage validation runs |
| `POLICIES_DIR` | `policies` | Path to YAML policy files |
| `REPORTS_DIR` | `reports` | Output directory for Markdown reports |

---

## GitHub Actions

The workflow in [.github/workflows/governance_agent.yml](.github/workflows/governance_agent.yml)
triggers on every pull request. Required secrets:

- `OPENAI_API_KEY`

For manual `workflow_dispatch` runs, the workflow accepts `base_ref` and `head_ref`
inputs and forwards them to the GitHub Actions runner. The current default branch refs are
`features/hexagonal-llm-migration/refactor-agent` for `base_ref` and
`features/hexagonal-llm-migration/main` for `head_ref`.

Each CI run now publishes:

- a Markdown report artifact under `governance-report-<run_id>`
- step outputs including `run_id`, `report_path`, `governance_status`, and `validation_status`
- a GitHub step summary with the same run metadata for quick inspection

If `OPENAI_API_KEY` is missing in GitHub Actions, the runner fails fast with a clear
configuration error instead of silently continuing with degraded CI behavior.

---

## Architecture Summary

### How Hexagonal Architecture was applied

The project is divided into four concentric rings:

1. **Domain** — Contains `ChangedFile`, `CodeScope`, `RefactorSuggestion`,
   `EngineeringPolicy`, `ValidationResult`, etc. Zero dependencies on frameworks
   or infrastructure. Can be unit-tested in pure Python with no mocking.

2. **Application** — Hosts the 8 focused use cases, the `RefactorSafetyPolicy`,
   the `RunEngineeringGovernanceAgentUseCase` orchestrator, and all port
   interfaces (`GitDiffReaderPort`, `LlmDocumentationGeneratorPort`, etc.).
   Depends only on the domain. Never imports from `infrastructure`.

3. **Infrastructure** — Implements every outbound port with concrete adapters
   (`GitDiffReaderAdapter`, `LlmDocumentationGeneratorAdapter`, etc.).
   All external tool calls, filesystem access, subprocess invocations, and
   HTTP calls live here. Adapters translate technical exceptions before they
   cross the boundary into the application layer.

4. **Entrypoints / Bootstrap** — `app/entrypoints/cli/main.py` and
   `app/entrypoints/github_actions/runner.py` are thin shells: parse context,
   build `AgentRunRequest`, call `RunAgentPort`, translate the response to an
   exit code. `app/bootstrap/container.py` is the sole place where concrete
   classes are instantiated and wired together.

### How SRP was enforced

Each class has exactly one reason to change:

| Class | Sole responsibility |
|---|---|
| `DiffParser` | Parse unified diff text → domain entities |
| `GitDiffReaderAdapter` | Invoke `git diff` subprocess |
| `AnalyzeDiffScopeUseCase` | Coordinate diff reading + future filtering |
| `RefactorSafetyPolicy` | Evaluate policy-level safety rules |
| `ValidateRefactorSafetyUseCase` | Sequence policy + tool validation |
| `MarkdownReportPublisherAdapter` | Serialise result → Markdown file |
| `RunEngineeringGovernanceAgentUseCase` | Sequence all pipeline steps |
| `build_container()` | Wire ports to adapters |

### Layer responsibility summary

| Layer | Owns |
|---|---|
| Domain | Business rules, entities, value objects, pure domain services |
| Application | Use case logic, port contracts, application-level policies |
| Infrastructure | Adapter implementations, config loading, console logging |
| Entrypoints | Request parsing, response mapping, exit-code translation |
| Bootstrap | Object construction and dependency wiring |

### How this scaffold evolves into the full agent

1. **Implement `DiffParser`** — add real unified-diff parsing in `infrastructure/parsers/`.
2. **Implement LLM adapters** — build prompts from `ChangedFile + EngineeringPolicy`,
   call the OpenAI API, parse structured JSON output into domain objects.
3. **Implement `YamlPolicyLoaderAdapter`** — add YAML schema and loader logic;
   create policy files under `policies/<profile>.yaml`.
4. **Implement `ProjectStructureReaderAdapter`** — add framework/test-runner detection heuristics.
5. **Add `ValidationRunnerPort` adapter** — run `pytest --co` or `ruff` on generated patches.
6. **Add `RefactorExecutorPort` adapter** — write patches to disk, create git commits.
7. **Extend the orchestrator** with patch application and PR comment publishing steps.
8. **Add integration tests** under `tests/integration/` for each adapter.
