from langgraph.graph import END, START, StateGraph

from app.clients.rss_news_client import RssNewsClient
from app.services.news_ranking_service import NewsRankingService
from app.services.news_relevance_service import NewsRelevanceService
from app.services.news_search_service import NewsSearchService
from app.services.news_summary_service import NewsSummaryService
from app.state import AgentState


rss_client = RssNewsClient()
news_search_service = NewsSearchService(rss_client=rss_client)
news_relevance_service = NewsRelevanceService()
news_ranking_service = NewsRankingService()
news_summary_service = NewsSummaryService()

MAX_RETRIES_PER_NODE = 2


def _register_failure(state: AgentState, node_name: str, message: str) -> AgentState:
    retries = dict(state.get("retry_counts", {}))
    retries[node_name] = retries.get(node_name, 0) + 1

    return {
        "error": message,
        "failed_node": node_name,
        "retry_counts": retries,
    }


def _clear_failure_state(state: AgentState) -> AgentState:
    retries = dict(state.get("retry_counts", {}))
    return {
        "error": "",
        "failed_node": "",
        "retry_counts": retries,
    }


def _should_retry_current_node(state: AgentState, node_name: str) -> bool:
    if not state.get("error"):
        return False
    if state.get("failed_node") != node_name:
        return False

    retries = state.get("retry_counts", {})
    return retries.get(node_name, 0) <= MAX_RETRIES_PER_NODE


def _route_after_fetch(state: AgentState) -> str:
    if _should_retry_current_node(state, "fetch_news"):
        return "fetch_news"
    if state.get("error"):
        return "summarize_news"
    return "filter_relevant_news"


def _route_after_filter(state: AgentState) -> str:
    if _should_retry_current_node(state, "filter_relevant_news"):
        return "fetch_news"
    if state.get("error"):
        return "summarize_news"
    return "rank_news"


def _route_after_rank(state: AgentState) -> str:
    if _should_retry_current_node(state, "rank_news"):
        return "filter_relevant_news"
    return "summarize_news"


def _route_after_summarize(state: AgentState) -> str:
    if _should_retry_current_node(state, "summarize_news"):
        return "rank_news"
    return END


def fetch_news_node(state: AgentState) -> AgentState:
    query = state.get("query", "últimas noticias")

    try:
        news_results = news_search_service.search_santa_fe_news(
            query=query,
            max_results=5,
        )

        print("=" * 80)
        print(f"FETCH NODE OUTPUT COUNT: {len(news_results)}")
        for idx, item in enumerate(news_results, start=1):
            print(f"{idx}. {item['title']}")

        return {
            "news_results": news_results,
            **_clear_failure_state(state),
        }
    except Exception as exc:
        return {
            "news_results": [],
            **_register_failure(state, "fetch_news", f"Error fetching news: {str(exc)}"),
        }


def filter_relevant_news_node(state: AgentState) -> AgentState:
    try:
        filtered_news_results = news_relevance_service.filter_relevant_news(
            state.get("news_results", [])
        )

        print("=" * 80)
        print(f"FILTER NODE OUTPUT COUNT: {len(filtered_news_results)}")
        for idx, item in enumerate(filtered_news_results, start=1):
            print(f"{idx}. {item['title']}")

        return {
            "filtered_news_results": filtered_news_results,
            **_clear_failure_state(state),
        }
    except Exception as exc:
        return {
            "filtered_news_results": [],
            **_register_failure(
                state,
                "filter_relevant_news",
                f"Error filtering news: {str(exc)}",
            ),
        }


def rank_news_node(state: AgentState) -> AgentState:
    try:
        filtered_news = state.get("filtered_news_results", [])
        raw_news = state.get("news_results", [])
        news_to_rank = filtered_news if filtered_news else raw_news

        ranked_news_results = news_ranking_service.rank_news(
            news_to_rank,
            top_k=4,
        )

        print("=" * 80)
        print(f"RANK NODE OUTPUT COUNT: {len(ranked_news_results)}")
        for idx, item in enumerate(ranked_news_results, start=1):
            print(f"{idx}. {item['title']}")

        return {
            "ranked_news_results": ranked_news_results,
            **_clear_failure_state(state),
        }
    except Exception as exc:
        return {
            "ranked_news_results": [],
            **_register_failure(state, "rank_news", f"Error ranking news: {str(exc)}"),
        }


def summarize_news_node(state: AgentState) -> AgentState:
    # If an upstream node failed and exceeded retries, end with explicit error output.
    if state.get("error") and not _should_retry_current_node(
        state, state.get("failed_node", "")
    ):
        return {
            "final_answer": f"No fue posible completar el proceso. Detalle: {state['error']}"
        }

    try:
        ranked_news = state.get("ranked_news_results", [])
        filtered_news = state.get("filtered_news_results", [])
        raw_news = state.get("news_results", [])

        if ranked_news:
            news_to_summarize = ranked_news
        elif filtered_news:
            news_to_summarize = filtered_news
        else:
            news_to_summarize = raw_news

        final_answer = news_summary_service.summarize_santa_fe_news(news_to_summarize)

        return {
            "final_answer": final_answer,
            **_clear_failure_state(state),
        }
    except Exception as exc:
        return {
            "final_answer": f"Falló la generación del resumen. Detalle: {str(exc)}",
            **_register_failure(
                state,
                "summarize_news",
                f"Error summarizing news: {str(exc)}",
            ),
        }


def build_graph():
    graph_builder = StateGraph(AgentState)

    graph_builder.add_node("fetch_news", fetch_news_node)
    graph_builder.add_node("filter_relevant_news", filter_relevant_news_node)
    graph_builder.add_node("rank_news", rank_news_node)
    graph_builder.add_node("summarize_news", summarize_news_node)

    graph_builder.add_edge(START, "fetch_news")
    graph_builder.add_conditional_edges(
        "fetch_news",
        _route_after_fetch,
        {
            "fetch_news": "fetch_news",
            "filter_relevant_news": "filter_relevant_news",
            "summarize_news": "summarize_news",
        },
    )
    graph_builder.add_conditional_edges(
        "filter_relevant_news",
        _route_after_filter,
        {
            "fetch_news": "fetch_news",
            "rank_news": "rank_news",
            "summarize_news": "summarize_news",
        },
    )
    graph_builder.add_conditional_edges(
        "rank_news",
        _route_after_rank,
        {
            "filter_relevant_news": "filter_relevant_news",
            "summarize_news": "summarize_news",
        },
    )
    graph_builder.add_conditional_edges(
        "summarize_news",
        _route_after_summarize,
        {
            "rank_news": "rank_news",
            END: END,
        },
    )

    return graph_builder.compile()