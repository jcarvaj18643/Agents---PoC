# USD/COP Intelligent Market Analysis Agent (PoC)

Production-style PoC of an agentic system that assesses directional pressure on USD/COP using market data, macro context, and recent news.

## Scope

- Scenario-based USD/COP analysis (up/down/mixed).
- Includes directional forecast range (estimated COP move) for the configured horizon.
- Explicit distinction between facts, signals, interpretation, recommendation, and uncertainty.
- Not a price predictor and NOT financial advice.

## Architecture

- Orchestrator: LangGraph
- State model: `app/state.py` (`AgentState`)
- Clean modular design:
  - `clients/` for external data and LLM access
  - `services/` for business logic
  - `nodes/` for thin graph orchestration
  - `domain/` for models

## Graph flow

`START -> fetch_market_data -> fetch_news (+5-day historical overlay) -> analyze_macro_context -> extract_signals -> filter_relevant_news -> rank_signals -> validate_analysis -> (retry fetch_news OR continue) -> build_scenarios -> build_recommendation (stores analysis snapshot) -> END`

## Fallback/retry behavior

- Market data failures: partial data with warnings.
- Weak news quality: retry path broadens news query.
- News historical memory: keeps a rolling 5-day local news cache and merges it into each run when relevant.
- Analysis historical memory: stores query/decision/confidence snapshots for a 5-day trend note.
- Ranking failure: fallback to unranked signals.
- Scenario LLM failure: deterministic scenario payload.
- Validation gate controls retry/degraded mode; no infinite loops (`retry_count` and `max_retries`).

## Historical storage

- Local files are created automatically under `data/history/`.
- `news_history.json`: rolling cache of deduplicated news items.
- `analysis_history.json`: rolling snapshots of recent run outcomes.
- Window is controlled by `HISTORY_WINDOW_DAYS` (default `5`).

## Run locally

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create env file:

```bash
cp .env.example .env
```

4. Run:

```bash
python -m app.main
```

## Current assumptions

- Public/free endpoints can be delayed or intermittently unavailable.
- Macro narratives are proxy-based in this PoC and should be upgraded with institutional data providers.

## Limitations

- Not an execution system and not investment advice.
- Data quality may vary across free sources.
- LLM output can vary and should be monitored.

## Next improvements

- Add institutional-grade market/macro providers with robust data contracts.
- Add caching, circuit breakers, and telemetry.
- Add backtesting/evaluation harness for signal quality.
- Add multilingual report mode and API entrypoint.

## Email settings notes

- `SENDGRID_TO_EMAIL` supports multiple recipients separated by commas.
- `SENDGRID_FROM_EMAIL` can include commas, but only the first address is used as sender.
