from __future__ import annotations

from datetime import UTC, datetime
import re
from html import unescape

from app.services.forecast_learning_service import ForecastLearningService


class RecommendationService:
    def __init__(self, learning_service: ForecastLearningService | None = None) -> None:
        self.learning_service = learning_service or ForecastLearningService()

    def _direction_call(self, signals: list[dict[str, str | float]]) -> tuple[str, str, str]:
        up_score = 0.0
        down_score = 0.0

        for signal in signals:
            weight = signal.get("weight", 0.0)
            score = float(weight) if isinstance(weight, (int, float)) else 0.0
            direction = str(signal.get("direction", "mixed"))
            if direction == "up":
                up_score += score
            elif direction == "down":
                down_score += score

        delta = up_score - down_score
        if delta > 0.35:
            return "up", "UP", "ALCISTA USD"
        if delta < -0.35:
            return "down", "DOWN", "BAJISTA USD"
        return "mixed", "MIXED", "MIXTO/INCIERTO"

    def _t(self, use_spanish: bool, es: str, en: str) -> str:
        return es if use_spanish else en

    def _forecast_range(
        self,
        ranked_signals: list[dict[str, str | float]],
        confidence_level: str,
        market_data: dict[str, object],
    ) -> tuple[str, str]:
        up_score = 0.0
        down_score = 0.0
        for signal in ranked_signals:
            raw_weight = signal.get("weight", 0.0)
            weight = float(raw_weight) if isinstance(raw_weight, (int, float)) else 0.0
            direction = str(signal.get("direction", "mixed"))
            if direction == "up":
                up_score += weight
            elif direction == "down":
                down_score += weight

        intensity = abs(up_score - down_score) / max(up_score + down_score, 1.0)
        confidence_scale = {
            "low": 0.45,
            "medium": 0.75,
            "high": 1.0,
        }.get(confidence_level.lower(), 0.7)

        mid_pct = max(0.0025, min(0.018, 0.009 * intensity * confidence_scale))
        low_pct = max(0.0015, mid_pct * 0.65)
        high_pct = max(0.0030, mid_pct * 1.35)

        learning_factor, learning_note, learning_samples = self.learning_service.calibration_factor()
        low_pct = max(0.0010, min(0.0300, low_pct * learning_factor))
        high_pct = max(low_pct + 0.0005, min(0.0500, high_pct * learning_factor))

        learning_es = ""
        learning_en = ""
        if learning_note:
            learning_es = (
                f" Autoaprendizaje activo ({learning_samples} muestras): "
                f"ajuste multiplicador={learning_factor:.4f} basado en {learning_note}."
            )
            learning_en = (
                f" Self-learning active ({learning_samples} samples): "
                f"multiplier adjustment={learning_factor:.4f} based on {learning_note}."
            )

        raw_spot = market_data.get("trm_current")
        if raw_spot is None:
            raw_spot = market_data.get("usd_cop")
        try:
            spot = float(raw_spot) if raw_spot is not None else 4050.0
        except (TypeError, ValueError):
            spot = 4050.0

        direction, _, _ = self._direction_call(ranked_signals)
        low_cop = round(spot * low_pct)
        high_cop = round(spot * high_pct)

        if direction == "up":
            es = (
                f"TRM actual: {spot:.2f} | Subida estimada: +{low_cop} a +{high_cop} COP "
                f"({low_pct*100:.2f}% a {high_pct*100:.2f}%). "
                f"TRM proyectada final: {spot + low_cop:.2f} a {spot + high_cop:.2f}."
                f"{learning_es}"
            )
            en = (
                f"Current TRM: {spot:.2f} | Estimated move up: +{low_cop} to +{high_cop} COP "
                f"({low_pct*100:.2f}% to {high_pct*100:.2f}%). "
                f"Projected final TRM: {spot + low_cop:.2f} to {spot + high_cop:.2f}."
                f"{learning_en}"
            )
            return es, en
        if direction == "down":
            es = (
                f"TRM actual: {spot:.2f} | Bajada estimada: -{high_cop} a -{low_cop} COP "
                f"(-{high_pct*100:.2f}% a -{low_pct*100:.2f}%). "
                f"TRM proyectada final: {spot - high_cop:.2f} a {spot - low_cop:.2f}."
                f"{learning_es}"
            )
            en = (
                f"Current TRM: {spot:.2f} | Estimated move down: -{high_cop} to -{low_cop} COP "
                f"(-{high_pct*100:.2f}% to -{low_pct*100:.2f}%). "
                f"Projected final TRM: {spot - high_cop:.2f} to {spot - low_cop:.2f}."
                f"{learning_en}"
            )
            return es, en

        es = (
            f"TRM actual: {spot:.2f} | Rango lateral estimado: {spot-high_cop:.2f} a {spot+high_cop:.2f} COP "
            f"(aprox. +/-{high_pct*100:.2f}%). TRM proyectada final: {spot:.2f}."
            f"{learning_es}"
        )
        en = (
            f"Current TRM: {spot:.2f} | Estimated sideways range: {spot-high_cop:.2f} to {spot+high_cop:.2f} COP "
            f"(about +/-{high_pct*100:.2f}%). Projected final TRM: {spot:.2f}."
            f"{learning_en}"
        )
        return es, en

    def _shorten(self, text: str, max_len: int = 180) -> str:
        clean = " ".join(text.split())
        if len(clean) <= max_len:
            return clean
        return clean[: max_len - 3].rstrip() + "..."

    def _clean_news_summary(self, text: str) -> str:
        no_tags = re.sub(r"<[^>]+>", " ", text)
        return self._shorten(unescape(no_tags), 160)

    def _append_historical_variables(
        self,
        lines: list[str],
        use_spanish: bool,
        ranked_signals: list[dict[str, str | float]],
    ) -> None:
        lines.append(self._t(use_spanish, "Variables historicas evaluadas", "Historical variables evaluated"))
        tracked = (
            "Rate differential (Fed vs BanRep)",
            "DXY context",
            "Oil context",
            "Risk sentiment via VIX",
            "Macro risk-off regime",
            "Macro risk-on regime",
            "Colombia inflation stickiness",
            "News macro tone balance",
        )
        present_names = {str(s.get('name', '')) for s in ranked_signals}
        for variable_name in tracked:
            status = self._t(use_spanish, "detectada", "detected") if variable_name in present_names else self._t(use_spanish, "sin dato reciente", "no recent data")
            lines.append(f"- {variable_name}: {status}")
        lines.append("")

    def _append_balance(
        self,
        lines: list[str],
        use_spanish: bool,
        bullish: list[dict[str, str | float]],
        bearish: list[dict[str, str | float]],
        mixed: list[dict[str, str | float]],
    ) -> None:
        lines.append(self._t(use_spanish, "Balance direccional", "Directional pressure balance"))
        lines.append(f"- {self._t(use_spanish, 'Senales alcistas USD', 'USD bullish signals')}: {len(bullish)}")
        lines.append(f"- {self._t(use_spanish, 'Senales bajistas USD', 'USD bearish signals')}: {len(bearish)}")
        lines.append(f"- {self._t(use_spanish, 'Factores mixtos', 'Mixed factors')}: {len(mixed)}")
        lines.append("")

    def build_final_recommendation(
        self,
        user_query: str,
        query_timestamp: str,
        analysis_horizon: str,
        confidence_level: str,
        ranked_signals: list[dict[str, str | float]],
        filtered_news: list[dict[str, str]],
        market_data: dict[str, object],
        scenario_analysis: dict[str, object],
        warnings: list[str],
        assumptions: list[str],
        output_language: str,
    ) -> str:
        use_spanish = output_language == "spanish"

        bullish = [s for s in ranked_signals if s.get("direction") == "up"]
        bearish = [s for s in ranked_signals if s.get("direction") == "down"]
        mixed = [s for s in ranked_signals if s.get("direction") == "mixed"]

        _, direction_en, direction_es = self._direction_call(ranked_signals)
        direction_label = direction_es if use_spanish else direction_en
        decision_es_map = {
            "ALCISTA USD": "al alza",
            "BAJISTA USD": "a la baja",
            "MIXTO/INCIERTO": "mixto",
        }
        decision_en_map = {
            "UP": "up",
            "DOWN": "down",
            "MIXED": "mixed",
        }
        decision_text = (
            decision_es_map.get(direction_es, "mixto")
            if use_spanish
            else decision_en_map.get(direction_en, "mixed")
        )

        lines: list[str] = []
        lines.append(self._t(use_spanish, "Respuesta directa", "Direct answer"))
        lines.append(
            f"- {self._t(use_spanish, 'Decision:', 'Decision:')} {decision_text}"
        )
        lines.append(
            f"- {self._t(use_spanish, 'Direccion estimada USD/COP (corto plazo):', 'Estimated USD/COP direction (short term):')} {direction_label}"
        )
        lines.append(
            f"- {self._t(use_spanish, 'Confianza:', 'Confidence:')} {confidence_level}"
        )
        forecast_es, forecast_en = self._forecast_range(
            ranked_signals=ranked_signals,
            confidence_level=confidence_level,
            market_data=market_data,
        )
        lines.append(
            f"- {self._t(use_spanish, 'Forecast probable (horizonte actual):', 'Likely forecast (current horizon):')} {self._t(use_spanish, forecast_es, forecast_en)}"
        )
        lines.append("")

        self._append_historical_variables(lines, use_spanish, ranked_signals)
        self._append_balance(lines, use_spanish, bullish, bearish, mixed)

        lines.append(self._t(use_spanish, "Senales clave", "Key signals"))
        for signal in ranked_signals[:6]:
            lines.append(
                f"- {signal['name']} | direction={signal['direction']} | weight={signal['weight']} | {signal.get('rationale', '')}"
            )
        lines.append("")

        lines.append(self._t(use_spanish, "Noticias relevantes (<= 7 dias)", "Relevant news (<= 7 days)"))
        if filtered_news:
            for item in filtered_news[:5]:
                lines.append(
                    f"- {item.get('title', '')} ({item.get('source', 'unknown source')})"
                )
        else:
            lines.append(
                f"- {self._t(use_spanish, 'No se encontraron noticias frescas suficientes.', 'No sufficient fresh news found.') }"
            )
        lines.append("")

        lines.append(self._t(use_spanish, "Escenarios", "Scenarios"))
        lines.append(f"- {self._t(use_spanish, 'A) USD/COP sube', 'A) USD/COP up')}")
        lines.append(f"- {self._t(use_spanish, 'B) USD/COP baja', 'B) USD/COP down')}")
        lines.append(f"- {self._t(use_spanish, 'C) USD/COP mixto/lateral', 'C) USD/COP mixed/sideways')}")
        llm_scenario_text = scenario_analysis.get("llm_scenario_text")
        if isinstance(llm_scenario_text, str) and llm_scenario_text.strip():
            lines.append(self._t(use_spanish, "Resumen narrativo:", "Narrative summary:"))
            lines.append(llm_scenario_text.strip())
        lines.append("")

        lines.append(self._t(use_spanish, "Riesgos principales", "Main risks"))
        if warnings:
            for warning in warnings[:5]:
                lines.append(f"- {warning}")
        else:
            lines.append(
                f"- {self._t(use_spanish, 'Sin alertas criticas del sistema.', 'No critical system warnings.') }"
            )
        lines.append("")

        lines.append(self._t(use_spanish, "Disclaimer", "Disclaimer"))
        lines.append(
            self._t(
                use_spanish,
                "Este resultado es analisis por escenarios y NO es asesoria financiera.",
                "This output is scenario-based analysis and is NOT financial advice.",
            )
        )
        lines.append("")

        lines.append(self._t(use_spanish, "Supuestos", "Assumptions"))
        for assumption in assumptions:
            lines.append(f"- {assumption}")

        lines.append("")
        lines.append(self._t(use_spanish, "Metadatos de consulta", "Query metadata"))
        if query_timestamp:
            lines.append(f"- {self._t(use_spanish, 'Fecha de consulta:', 'Consultation date:')} {query_timestamp}")
        else:
            lines.append(f"- {self._t(use_spanish, 'Fecha de consulta:', 'Consultation date:')} {datetime.now(UTC).isoformat()}")
        lines.append(f"- {self._t(use_spanish, 'Titulo de la consulta:', 'Query title:')} {user_query}")
        lines.append(f"- {self._t(use_spanish, 'Resumen breve:', 'Short summary:')} {self._shorten(user_query, 140)}")
        lines.append(f"- {self._t(use_spanish, 'Horizonte:', 'Horizon:')} {analysis_horizon}")

        lines.append("")
        lines.append(self._t(use_spanish, "Noticias mas relevantes para la decision", "Most relevant news for the decision"))
        if filtered_news:
            for item in filtered_news[:5]:
                news_title = str(item.get("title", ""))
                news_date = str(item.get("published", "N/A"))
                news_link = str(item.get("link", ""))
                news_summary = self._clean_news_summary(str(item.get("summary", "")))
                lines.append(f"- {self._t(use_spanish, 'Fecha:', 'Date:')} {news_date}")
                lines.append(f"- {self._t(use_spanish, 'Titulo:', 'Title:')} {news_title}")
                lines.append(f"- {self._t(use_spanish, 'URL:', 'URL:')} {news_link}")
                lines.append(f"- {self._t(use_spanish, 'Resumen:', 'Summary:')} {news_summary}")
        else:
            lines.append(f"- {self._t(use_spanish, 'Sin noticias relevantes recientes para anexar.', 'No recent relevant news to append.')}")

        lines.append("")
        lines.append(f"{self._t(use_spanish, 'Consulta analizada', 'Analyzed query')}: {user_query}")

        return "\n".join(lines)
