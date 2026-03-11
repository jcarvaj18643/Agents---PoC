from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph

from app.clients.llm_client import LLMClientFactory
from app.clients.macro_data_client import MacroDataClient
from app.clients.market_data_client import MarketDataClient
from app.clients.news_client import NewsClient
from app.clients.sendgrid_client import SendGridClient
from app.nodes import (
    analyze_macro_node,
    build_recommendation_node,
    build_scenarios_node,
    extract_signals_node,
    fetch_market_data_node,
    fetch_news_node,
    filter_news_node,
    rank_signals_node,
    send_email_node,
    validate_analysis_node,
)
from app.services.fallback_service import FallbackService
from app.services.analysis_history_service import AnalysisHistoryService
from app.services.macro_analysis_service import MacroAnalysisService
from app.services.market_data_service import MarketDataService
from app.services.news_service import NewsService
from app.services.ranking_service import RankingService
from app.services.email_service import EmailService
from app.services.forecast_learning_service import ForecastLearningService
from app.services.recommendation_service import RecommendationService
from app.services.relevance_service import RelevanceService
from app.services.scenario_service import ScenarioService
from app.services.signal_extraction_service import SignalExtractionService
from app.services.validation_service import ValidationService
from app.state import AgentState


logger = logging.getLogger(__name__)


market_data_service = MarketDataService(MarketDataClient())
news_service = NewsService(NewsClient())
macro_service = MacroAnalysisService(MacroDataClient())
signal_service = SignalExtractionService()
relevance_service = RelevanceService()
ranking_service = RankingService()
validation_service = ValidationService()
fallback_service = FallbackService()
forecast_learning_service = ForecastLearningService()
scenario_service = ScenarioService(LLMClientFactory())
recommendation_service = RecommendationService()
analysis_history_service = AnalysisHistoryService()
email_service = EmailService(SendGridClient())


def _safe_node_execution(node_name: str, node_fn, state: AgentState) -> AgentState:
    try:
        return node_fn(state)
    except Exception as exc:
        logger.exception("node=%s unhandled_error=%s", node_name, exc)
        warnings = list(state.get("warnings", []))
        warnings.append(f"Unhandled error in {node_name}: {exc}")
        return {
            "error": f"{node_name} failed: {exc}",
            "warnings": warnings,
            "degraded_mode": True,
            "confidence_level": "low",
            "route_hint": "build_scenarios",
        }


def fetch_market_data(state: AgentState) -> AgentState:
    return _safe_node_execution(
        "fetch_market_data",
        lambda s: fetch_market_data_node.run(s, market_data_service),
        state,
    )


def fetch_news(state: AgentState) -> AgentState:
    return _safe_node_execution(
        "fetch_news",
        lambda s: fetch_news_node.run(s, news_service),
        state,
    )


def analyze_macro_context(state: AgentState) -> AgentState:
    return _safe_node_execution(
        "analyze_macro_context",
        lambda s: analyze_macro_node.run(s, macro_service),
        state,
    )


def extract_signals(state: AgentState) -> AgentState:
    return _safe_node_execution(
        "extract_signals",
        lambda s: extract_signals_node.run(s, signal_service),
        state,
    )


def filter_relevant_news(state: AgentState) -> AgentState:
    return _safe_node_execution(
        "filter_relevant_news",
        lambda s: filter_news_node.run(s, relevance_service),
        state,
    )


def rank_signals(state: AgentState) -> AgentState:
    return _safe_node_execution(
        "rank_signals",
        lambda s: rank_signals_node.run(s, ranking_service),
        state,
    )


def validate_analysis(state: AgentState) -> AgentState:
    return _safe_node_execution(
        "validate_analysis",
        lambda s: validate_analysis_node.run(s, validation_service, fallback_service, forecast_learning_service),
        state,
    )


def build_scenarios(state: AgentState) -> AgentState:
    return _safe_node_execution(
        "build_scenarios",
        lambda s: build_scenarios_node.run(s, scenario_service),
        state,
    )


def build_recommendation(state: AgentState) -> AgentState:
    return _safe_node_execution(
        "build_recommendation",
        lambda s: build_recommendation_node.run(s, recommendation_service, analysis_history_service),
        state,
    )


def send_email(state: AgentState) -> AgentState:
    return _safe_node_execution(
        "send_email",
        lambda s: send_email_node.run(s, email_service),
        state,
    )


def route_after_validation(state: AgentState) -> str:
    route_hint = state.get("route_hint", "build_scenarios")
    if route_hint == "retry_fetch_market_data":
        return "fetch_market_data"
    if route_hint == "retry_fetch_news":
        return "fetch_news"
    return "build_scenarios"


def build_graph():
    logger.info("graph_start")
    graph = StateGraph(AgentState)

    graph.add_node("fetch_market_data", fetch_market_data)
    graph.add_node("fetch_news", fetch_news)
    graph.add_node("analyze_macro_context", analyze_macro_context)
    graph.add_node("extract_signals", extract_signals)
    graph.add_node("filter_relevant_news", filter_relevant_news)
    graph.add_node("rank_signals", rank_signals)
    graph.add_node("validate_analysis", validate_analysis)
    graph.add_node("build_scenarios", build_scenarios)
    graph.add_node("build_recommendation", build_recommendation)
    graph.add_node("send_email", send_email)

    graph.add_edge(START, "fetch_market_data")
    graph.add_edge("fetch_market_data", "fetch_news")
    graph.add_edge("fetch_news", "analyze_macro_context")
    graph.add_edge("analyze_macro_context", "extract_signals")
    graph.add_edge("extract_signals", "filter_relevant_news")
    graph.add_edge("filter_relevant_news", "rank_signals")
    graph.add_edge("rank_signals", "validate_analysis")

    graph.add_conditional_edges(
        "validate_analysis",
        route_after_validation,
        {
            "fetch_market_data": "fetch_market_data",
            "fetch_news": "fetch_news",
            "build_scenarios": "build_scenarios",
        },
    )

    graph.add_edge("build_scenarios", "build_recommendation")
    graph.add_edge("build_recommendation", "send_email")
    graph.add_edge("send_email", END)

    return graph.compile()
