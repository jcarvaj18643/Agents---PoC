from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys

# Allow execution from project root or from inside app/ folder.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings
from app.graph import build_graph
from app.state import AgentState


def normalize_output_language(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"es", "spanish", "espanol", "español"}:
        return "spanish"
    if normalized in {"en", "english", "ingles", "inglés"}:
        return "english"
    return "spanish"


def build_initial_state(user_query: str, horizon: str, output_language: str) -> AgentState:
    return {
        "user_query": user_query,
        "query_timestamp": datetime.now(UTC).isoformat(),
        "analysis_horizon": horizon,
        "output_language": output_language,
        "market_data": {},
        "macro_data": {},
        "raw_news": [],
        "filtered_news": [],
        "historical_news_used": 0,
        "historical_analysis_used": 0,
        "extracted_signals": [],
        "ranked_signals": [],
        "scenario_analysis": {},
        "final_recommendation": "",
        "executive_summary": "",
        "email_sent": False,
        "email_error": None,
        "assumptions": [
            "PoC uses public/free market and news sources that may be delayed.",
            "Directional pressure is scenario-based, not deterministic prediction.",
            "Macro narratives are partially proxy-based and should be validated with institutional feeds.",
        ],
        "warnings": [],
        "error": None,
        "retry_count": 0,
        "max_retries": settings.max_retries,
        "fallback_reason": None,
        "degraded_mode": False,
        "confidence_level": "medium",
        "validation_passed": False,
        "validation_issues": [],
        "route_hint": "build_scenarios",
    }


def main() -> None:
    current_hour = datetime.now().hour
    if current_hour < settings.run_start_hour or current_hour > settings.run_end_hour:
        return

    user_query = settings.default_user_query
    horizon = settings.default_analysis_horizon
    output_language = normalize_output_language(settings.default_output_language)

    graph = build_graph()
    initial_state = build_initial_state(
        user_query=user_query,
        horizon=horizon,
        output_language=output_language,
    )
    result = graph.invoke(initial_state)
    summary = str(result.get("executive_summary", "")).strip()
    if summary:
        print(summary)
        return

    # Fallback for unexpected paths where email node did not produce a summary.
    print("No executive summary produced.")


if __name__ == "__main__":
    main()
