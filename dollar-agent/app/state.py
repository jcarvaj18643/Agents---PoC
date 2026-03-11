from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    user_query: str
    query_timestamp: str
    analysis_horizon: str
    output_language: str

    market_data: dict[str, Any]
    macro_data: dict[str, Any]

    raw_news: list[dict[str, Any]]
    filtered_news: list[dict[str, Any]]
    historical_news_used: int
    historical_analysis_used: int

    extracted_signals: list[dict[str, Any]]
    ranked_signals: list[dict[str, Any]]

    scenario_analysis: dict[str, Any]
    final_recommendation: str
    executive_summary: str
    email_sent: bool
    email_error: str | None

    assumptions: list[str]
    warnings: list[str]

    error: str | None
    retry_count: int
    max_retries: int
    fallback_reason: str | None
    degraded_mode: bool
    confidence_level: str

    validation_passed: bool
    validation_issues: list[str]
    route_hint: str
