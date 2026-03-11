from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.clients.llm_client import LLMClientFactory


class ScenarioService:
    def __init__(self, llm_factory: LLMClientFactory) -> None:
        self.llm_factory = llm_factory

    def build(
        self,
        user_query: str,
        ranked_signals: list[dict[str, str | float]],
        filtered_news: list[dict[str, str]],
        degraded_mode: bool,
        output_language: str,
    ) -> tuple[dict[str, object], list[str]]:
        warnings: list[str] = []

        top_signals = ranked_signals[:6]

        deterministic_payload: dict[str, object] = {
            "scenario_up": {
                "title": "Scenario A: USD/COP likely up",
                "drivers": [s for s in top_signals if s.get("direction") == "up"],
            },
            "scenario_down": {
                "title": "Scenario B: USD/COP likely down",
                "drivers": [s for s in top_signals if s.get("direction") == "down"],
            },
            "scenario_mixed": {
                "title": "Scenario C: mixed/sideways",
                "drivers": [s for s in top_signals if s.get("direction") == "mixed"],
            },
            "news_count": len(filtered_news),
            "degraded_mode": degraded_mode,
        }

        try:
            llm = self.llm_factory.build()
            lang_hint = "Spanish" if output_language == "spanish" else "English"
            prompt = (
                "Build a concise scenario analysis for USD/COP using these top signals. "
                "Return compact markdown with sections: up, down, mixed, key uncertainties.\n\n"
                f"User query: {user_query}\n"
                f"Signals: {top_signals}\n"
                f"Relevant news count: {len(filtered_news)}\n"
                f"Write the answer in {lang_hint}. "
                "Do not give financial advice."
            )
            response = llm.invoke(
                [
                    SystemMessage(content="You are a macro FX analyst writing scenario-based analysis."),
                    HumanMessage(content=prompt),
                ]
            )
            deterministic_payload["llm_scenario_text"] = str(response.content)
        except Exception as exc:
            warnings.append(f"Scenario LLM generation failed, used deterministic scenario payload: {exc}")

        return deterministic_payload, warnings
