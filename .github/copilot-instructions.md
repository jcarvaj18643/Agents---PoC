# Copilot Instructions

These instructions apply to the whole workspace and must be treated as default coding rules.

## Architecture Baseline

- Use Hexagonal Architecture (Ports and Adapters).
- Keep business logic in `domain` and `application`.
- Keep framework and external integrations in `infrastructure`.
- Keep API/CLI/workers in `entrypoints`.
- Dependency direction must point inward.

## Layer Rules

- `domain` must not import infrastructure/framework code.
- `application` can depend on `domain` only.
- `infrastructure` implements ports defined by `application`.
- `entrypoints` only orchestrate requests/responses and wiring.

## SOLID Rules

- SRP: one reason to change per class/module.
- OCP: extend behavior via interfaces/adapters, avoid modifying stable core.
- LSP: implementations must respect port contracts.
- ISP: prefer small, focused interfaces.
- DIP: depend on abstractions, inject concrete implementations at composition root.

## Python Coding Rules

- Target Python 3.11+.
- Add type hints to public functions and class methods.
- Keep functions short and cohesive.
- Avoid business logic inside controllers/routes/CLI handlers.
- Use constructor dependency injection for services.

## Ports and Adapters

- Define ports in `application/ports` using Protocol or ABC.
- Implement adapters in `infrastructure/adapters`.
- Never instantiate external clients inside domain entities/use cases.

## Error Handling

- Model domain errors explicitly (`domain/exceptions.py`).
- Translate technical exceptions in adapters before crossing into application/domain.
- Avoid leaking infrastructure-specific exceptions to core business logic.

## Testing

- Prefer unit tests for domain and use cases.
- Add integration tests for adapters (DB, HTTP, LLM, queues).
- Unit tests must not hit network or filesystem.

## Quality Gates

- Format: `black`
- Lint: `ruff`
- Types: `mypy` or `pyright`
- Tests: `pytest`

## Pull Request Checklist

- Preserve hexagonal boundaries.
- Follow SOLID principles.
- Add/adjust tests for behavior changes.
- Keep changes minimal and focused.
- Document architectural decisions when needed.
