import argparse

from app.clients.llm_client import get_llm_call_count, reset_llm_call_count
from app.graph import build_graph


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Busca, filtra y resume noticias de Independiente Santa Fe."
    )
    parser.add_argument(
        "-q",
        "--query",
        default="últimas noticias",
        help="Consulta para buscar noticias (default: 'últimas noticias').",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    graph = build_graph()
    reset_llm_call_count()

    initial_state = {
        "query": args.query,
    }

    result = graph.invoke(initial_state)
    display_news = result.get("filtered_news_results") or result.get("news_results", [])

    print("=" * 80)
    print("RAW NEWS COUNT")
    print("=" * 80)
    print(len(result.get("news_results", [])))

    print("\n" + "=" * 80)
    print("FILTERED NEWS COUNT")
    print("=" * 80)
    print(len(display_news))

    print("\n" + "=" * 80)
    print("FILTERED NEWS")
    print("=" * 80)
    print("=" * 80)
    
    for index, item in enumerate(display_news, start=1):
        print(f"{index}. {item['title']}")
        print(f"   Source: {item['source']}")
        print(f"   Published: {item['published']}")
        print()

    print("FULL RESULT")
    print("=" * 80)
    print(result)
    
    print("\n" + "=" * 80)
    print("FINAL ANSWER")
    print("=" * 80)
    print(result.get("final_answer", "No final answer generated."))

    print("\n" + "=" * 80)
    print("LLM CALL COUNT")
    print("=" * 80)
    print(get_llm_call_count())


if __name__ == "__main__":
    main()