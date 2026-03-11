from __future__ import annotations

from datetime import datetime
from html import escape
import re
from html import unescape

from app.clients.sendgrid_client import SendGridClient
from app.config import settings
from app.services.forecast_tracking_service import ForecastTrackingService
from app.state import AgentState


class EmailService:
    def __init__(self, client: SendGridClient) -> None:
        self.client = client
        self.forecast_tracking = ForecastTrackingService()

    def _parse_emails(self, raw: str) -> list[str]:
        return [item.strip() for item in raw.split(",") if item.strip()]

    def _t(self, use_spanish: bool, es: str, en: str) -> str:
        return es if use_spanish else en

    def _clean_summary(self, text: str, max_len: int = 180) -> str:
        no_tags = re.sub(r"<[^>]+>", " ", text)
        clean = " ".join(unescape(no_tags).split())
        if len(clean) <= max_len:
            return clean
        return clean[: max_len - 3].rstrip() + "..."

    def _evaluated_variables(self, state: AgentState) -> list[str]:
        ranked_signals = state.get("ranked_signals", [])
        market_data = state.get("market_data", {})

        signal_catalog = (
            "Rate differential (Fed vs BanRep)",
            "DXY context",
            "Oil context",
            "Risk sentiment via VIX",
            "Macro risk-off regime",
            "Macro risk-on regime",
            "Colombia inflation stickiness",
            "News macro tone balance",
            "News flow momentum",
        )
        present_signal_names = {str(item.get("name", "")) for item in ranked_signals}

        lines: list[str] = []
        for name in signal_catalog:
            status = "detected" if name in present_signal_names else "no recent data"
            lines.append(f"{name}: {status}")

        lines.append("usd_cop spot: " + ("available" if market_data.get("usd_cop") is not None else "missing"))
        lines.append("dxy level: " + ("available" if market_data.get("dxy") is not None else "missing"))
        lines.append("brent_oil level: " + ("available" if market_data.get("brent_oil") is not None else "missing"))
        lines.append("sp500 level: " + ("available" if market_data.get("sp500") is not None else "missing"))
        lines.append("vix level: " + ("available" if market_data.get("vix") is not None else "missing"))
        return lines

    def _extract(self, final_text: str, fallback_confidence: str) -> tuple[str, str]:
        decision = "not available"
        confidence = fallback_confidence
        for line in final_text.splitlines():
            low = line.strip().lower()
            if low.startswith("- decision:"):
                decision = line.split(":", 1)[1].strip()
            elif low.startswith("- confianza:") or low.startswith("- confidence:"):
                confidence = line.split(":", 1)[1].strip()
        return decision, confidence

    def _extract_forecast_value(self, forecast_line: str) -> float | None:
        projected_match = re.search(
            r"TRM proyectada final:\s*(\d+(?:\.\d+)?)\s*a\s*(\d+(?:\.\d+)?)",
            forecast_line,
            flags=re.IGNORECASE,
        )
        if projected_match:
            low = float(projected_match.group(1))
            high = float(projected_match.group(2))
            return (low + high) / 2.0

        projected_single = re.search(
            r"TRM proyectada final:\s*(\d+(?:\.\d+)?)",
            forecast_line,
            flags=re.IGNORECASE,
        )
        if projected_single:
            return float(projected_single.group(1))

        # English fallback.
        projected_en = re.search(
            r"Projected final TRM:\s*(\d+(?:\.\d+)?)\s*to\s*(\d+(?:\.\d+)?)",
            forecast_line,
            flags=re.IGNORECASE,
        )
        if projected_en:
            low = float(projected_en.group(1))
            high = float(projected_en.group(2))
            return (low + high) / 2.0

        return None

    def _build_executive_summary(self, state: AgentState) -> tuple[str, str, str]:
        final_text = state.get("final_recommendation", "")
        decision, confidence = self._extract(
            final_text,
            fallback_confidence=str(state.get("confidence_level", "unknown")),
        )

        query = state.get("user_query", "")
        query_ts = state.get("query_timestamp", "")
        horizon = state.get("analysis_horizon", "")
        lang = state.get("output_language", "")
        use_spanish = str(lang).lower() == "spanish"
        warnings = state.get("warnings", [])[:3]
        top_signals = state.get("ranked_signals", [])[:3]
        relevant_news = state.get("filtered_news", [])[:4]
        forecast_line = "not available"
        for line in final_text.splitlines():
            low = line.strip().lower()
            if low.startswith("- forecast probable") or low.startswith("- likely forecast"):
                forecast_line = line.split(":", 1)[1].strip() if ":" in line else line
                break

        trm_raw = state.get("market_data", {}).get("trm_current")
        if trm_raw is None:
            trm_raw = state.get("market_data", {}).get("usd_cop")
        try:
            trm_current = float(trm_raw) if trm_raw is not None else None
        except (TypeError, ValueError):
            trm_current = None

        forecast_value = self._extract_forecast_value(forecast_line)
        csv_path, drift_pct = self.forecast_tracking.append_and_calculate_drift(
            trm_actual=trm_current,
            forecast=forecast_value,
            decision=decision,
            fecha=query_ts,
        )
        evaluated_variables = self._evaluated_variables(state)
        evaluated_variables.append("trm_current (TradingView preferred): " + ("available" if trm_current is not None else "missing"))
        if drift_pct is not None:
            evaluated_variables.append(f"forecast drift vs previous run: {drift_pct}%")
        else:
            evaluated_variables.append("forecast drift vs previous run: N/A")

        summary_lines = [
            self._t(use_spanish, "Resumen Ejecutivo", "Executive Summary"),
            f"{self._t(use_spanish, 'Decision', 'Decision')}: {decision}",
            f"{self._t(use_spanish, 'Confianza', 'Confidence')}: {confidence}",
            f"{self._t(use_spanish, 'Forecast', 'Forecast')}: {forecast_line}",
            f"{self._t(use_spanish, 'TRM actual (TradingView)', 'Current TRM (TradingView)')}: {('N/A' if trm_current is None else f'{trm_current:.2f}')}",
            f"{self._t(use_spanish, 'Consulta', 'Query')}: {query}",
            f"{self._t(use_spanish, 'Fecha de consulta', 'Query timestamp')}: {query_ts}",
            f"{self._t(use_spanish, 'Horizonte', 'Horizon')}: {horizon}",
            f"{self._t(use_spanish, 'Idioma de salida', 'Output language')}: {lang}",
            self._t(use_spanish, "Senales principales:", "Top signals:"),
        ]
        for signal in top_signals:
            summary_lines.append(
                f"- {signal.get('name')} ({signal.get('direction')}, w={signal.get('weight')})"
            )

        summary_lines.append(self._t(use_spanish, "Noticias relevantes para la decision:", "Relevant news for the decision:"))
        if relevant_news:
            for news in relevant_news:
                news_date = str(news.get("published", "N/A"))
                news_title = str(news.get("title", ""))
                news_link = str(news.get("link", ""))
                news_summary = self._clean_summary(str(news.get("summary", "")), max_len=140)
                summary_lines.append(f"- {self._t(use_spanish, 'Fecha', 'Date')}: {news_date}")
                summary_lines.append(f"- {self._t(use_spanish, 'Titulo', 'Title')}: {news_title}")
                summary_lines.append(f"- {self._t(use_spanish, 'URL', 'URL')}: {news_link}")
                summary_lines.append(f"- {self._t(use_spanish, 'Resumen', 'Summary')}: {news_summary}")
        else:
            summary_lines.append(
                f"- {self._t(use_spanish, 'Sin noticias relevantes recientes.', 'No recent relevant news.') }"
            )

        if warnings:
            summary_lines.append(self._t(use_spanish, "Alertas:", "Warnings:"))
            for warning in warnings:
                summary_lines.append(f"- {warning}")

        summary_lines.append(
            f"{self._t(use_spanish, 'Archivo de seguimiento', 'Tracking file')}: {csv_path}"
        )

        summary_lines.append(self._t(use_spanish, "Variables evaluadas:", "Evaluated variables:"))
        for item in evaluated_variables:
            summary_lines.append(f"- {item}")

        plain_text = "\n".join(summary_lines)

        html = [
            f"<h2>{escape(self._t(use_spanish, 'Resumen Ejecutivo USD/COP', 'USD/COP Executive Summary'))}</h2>",
            f"<p><b>{escape(self._t(use_spanish, 'Decision', 'Decision'))}:</b> {escape(decision)}</p>",
            f"<p><b>{escape(self._t(use_spanish, 'Confianza', 'Confidence'))}:</b> {escape(confidence)}</p>",
            f"<p><b>{escape(self._t(use_spanish, 'Forecast', 'Forecast'))}:</b> {escape(forecast_line)}</p>",
            f"<p><b>{escape(self._t(use_spanish, 'TRM actual (TradingView)', 'Current TRM (TradingView)'))}:</b> {escape('N/A' if trm_current is None else f'{trm_current:.2f}')}</p>",
            f"<h3>{escape(self._t(use_spanish, 'Parametros de entrada', 'Input Parameters'))}</h3>",
            f"<p><b>{escape(self._t(use_spanish, 'Consulta', 'Query'))}:</b> {escape(query)}</p>",
            f"<p><b>{escape(self._t(use_spanish, 'Fecha de consulta', 'Query timestamp'))}:</b> {escape(query_ts)}</p>",
            f"<p><b>{escape(self._t(use_spanish, 'Horizonte', 'Horizon'))}:</b> {escape(horizon)}</p>",
            f"<p><b>{escape(self._t(use_spanish, 'Idioma', 'Language'))}:</b> {escape(lang)}</p>",
            f"<h3>{escape(self._t(use_spanish, 'Senales principales', 'Top Signals'))}</h3>",
            "<ul>",
        ]
        for signal in top_signals:
            html.append(
                "<li>"
                + escape(str(signal.get("name")))
                + " | "
                + escape(str(signal.get("direction")))
                + " | weight="
                + escape(str(signal.get("weight")))
                + "</li>"
            )
        html.append("</ul>")

        html.append(f"<h3>{escape(self._t(use_spanish, 'Noticias relevantes para la decision', 'Relevant news for the decision'))}</h3>")
        if relevant_news:
            html.append("<ul>")
            for news in relevant_news:
                news_date = str(news.get("published", "N/A"))
                news_title = str(news.get("title", ""))
                news_link = str(news.get("link", ""))
                news_summary = self._clean_summary(str(news.get("summary", "")), max_len=180)
                html.append(
                    "<li>"
                    + f"<b>{escape(self._t(use_spanish, 'Fecha', 'Date'))}:</b> {escape(news_date)}<br>"
                    + f"<b>{escape(self._t(use_spanish, 'Titulo', 'Title'))}:</b> {escape(news_title)}<br>"
                    + f"<b>{escape(self._t(use_spanish, 'URL', 'URL'))}:</b> {escape(news_link)}<br>"
                    + f"<b>{escape(self._t(use_spanish, 'Resumen', 'Summary'))}:</b> {escape(news_summary)}"
                    + "</li>"
                )
            html.append("</ul>")
        else:
            html.append(f"<p>{escape(self._t(use_spanish, 'Sin noticias relevantes recientes.', 'No recent relevant news.'))}</p>")

        if warnings:
            html.append(f"<h3>{escape(self._t(use_spanish, 'Alertas', 'Warnings'))}</h3><ul>")
            for warning in warnings:
                html.append(f"<li>{escape(warning)}</li>")
            html.append("</ul>")

        html.append(
            f"<p><b>{escape(self._t(use_spanish, 'Archivo de seguimiento', 'Tracking file'))}:</b> {escape(csv_path)}</p>"
        )

        html.append(f"<h3>{escape(self._t(use_spanish, 'Variables evaluadas', 'Evaluated variables'))}</h3><ul>")
        for item in evaluated_variables:
            html.append(f"<li>{escape(item)}</li>")
        html.append("</ul>")

        html.append(
            "<p><i>"
            + escape(
                self._t(
                    use_spanish,
                    "Este analisis es por escenarios, solo informativo, y no constituye asesoria financiera.",
                    "This is scenario-based analysis for informational purposes only and is not financial advice.",
                )
            )
            + "</i></p>"
        )

        subject = f"{settings.sendgrid_subject_prefix} | {decision.upper()}"
        return subject, plain_text, "".join(html)

    def send_executive_summary(self, state: AgentState) -> tuple[bool, str | None, str]:
        subject, plain_text, html = self._build_executive_summary(state)

        if not settings.send_email_enabled:
            return False, None, plain_text

        now_hour = datetime.now().hour
        if now_hour not in settings.send_email_hours:
            return False, None, plain_text

        from_candidates = self._parse_emails(settings.sendgrid_from_email)
        to_candidates = self._parse_emails(settings.sendgrid_to_email)

        if not from_candidates or not to_candidates:
            return False, "Missing SENDGRID_FROM_EMAIL or SENDGRID_TO_EMAIL.", plain_text

        from_email = from_candidates[0]

        self.client.send_email(
            to_emails=to_candidates,
            from_email=from_email,
            from_name=settings.sendgrid_from_name,
            subject=subject,
            plain_text=plain_text,
            html=html,
        )
        return True, None, plain_text
