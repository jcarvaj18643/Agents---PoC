from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.config import settings
from app.utils.runtime_paths import project_root


class AnalysisHistoryService:
    def __init__(self) -> None:
        self.storage_path = project_root() / "data" / "history" / "analysis_history.json"

    def _read_entries(self) -> list[dict[str, str]]:
        if not self.storage_path.exists():
            return []

        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

        entries = payload.get("analyses") if isinstance(payload, dict) else None
        if not isinstance(entries, list):
            return []

        normalized: list[dict[str, str]] = []
        for item in entries:
            if isinstance(item, dict):
                normalized.append(
                    {
                        "timestamp": str(item.get("timestamp", "")),
                        "query": str(item.get("query", "")),
                        "decision": str(item.get("decision", "")),
                        "confidence": str(item.get("confidence", "")),
                    }
                )
        return normalized

    def _write_entries(self, entries: list[dict[str, str]]) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(
            json.dumps({"analyses": entries}, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    def _pruned(self, entries: list[dict[str, str]]) -> list[dict[str, str]]:
        cutoff = datetime.now(UTC) - timedelta(days=settings.history_window_days)
        kept: list[dict[str, str]] = []
        for item in entries:
            ts = item.get("timestamp", "")
            try:
                parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                continue
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            if parsed.astimezone(UTC) >= cutoff:
                kept.append(item)
        return kept

    def append(self, query: str, decision: str, confidence: str) -> None:
        now = datetime.now(UTC).isoformat()
        entries = self._pruned(self._read_entries())
        entries.append(
            {
                "timestamp": now,
                "query": query,
                "decision": decision,
                "confidence": confidence,
            }
        )
        self._write_entries(entries)

    def build_trend_note(self, output_language: str) -> str | None:
        entries = self._pruned(self._read_entries())
        if len(entries) < 2:
            return None

        last = entries[-3:]
        decisions = [e.get("decision", "").lower() for e in last]
        up_count = sum(1 for d in decisions if "al alza" in d or d == "up")
        down_count = sum(1 for d in decisions if "a la baja" in d or d == "down")

        if output_language == "spanish":
            if up_count > down_count:
                return "Tendencia historica (ultimos 5 dias): sesgo mayormente alcista en analisis recientes."
            if down_count > up_count:
                return "Tendencia historica (ultimos 5 dias): sesgo mayormente bajista en analisis recientes."
            return "Tendencia historica (ultimos 5 dias): sesgo mixto en analisis recientes."

        if up_count > down_count:
            return "5-day analysis trend: mostly bullish USD bias in recent runs."
        if down_count > up_count:
            return "5-day analysis trend: mostly bearish USD bias in recent runs."
        return "5-day analysis trend: mixed bias in recent runs."
