from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path

from app.utils.runtime_paths import project_root


class ForecastTrackingService:
    def __init__(self) -> None:
        self.csv_path = project_root() / "data" / "history" / "forecast_tracking.csv"

    def _read_rows(self) -> list[dict[str, str]]:
        if not self.csv_path.exists():
            return []

        with self.csv_path.open("r", newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            return [dict(row) for row in reader]

    def _write_rows(self, rows: list[dict[str, str]]) -> None:
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        headers = ["trm_actual", "forecast", "decision", "fecha", "desfase_pct"]
        with self.csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)

    def append_and_calculate_drift(
        self,
        trm_actual: float | None,
        forecast: float | None,
        decision: str,
        fecha: str | None = None,
    ) -> tuple[str, str | None]:
        rows = self._read_rows()

        sanitized_forecast = forecast
        if sanitized_forecast is not None and sanitized_forecast < 1000:
            sanitized_forecast = None

        previous_forecast: float | None = None
        if rows:
            prev_raw = rows[-1].get("forecast", "")
            try:
                parsed_prev = float(prev_raw)
                if parsed_prev >= 1000:
                    previous_forecast = parsed_prev
            except (TypeError, ValueError):
                previous_forecast = None

        drift_pct: str | None = None
        if previous_forecast and trm_actual is not None and previous_forecast != 0:
            drift = ((trm_actual - previous_forecast) / previous_forecast) * 100.0
            drift_pct = f"{drift:.4f}"

        record = {
            "trm_actual": "" if trm_actual is None else f"{trm_actual:.4f}",
            "forecast": "" if sanitized_forecast is None else f"{sanitized_forecast:.4f}",
            "decision": decision,
            "fecha": fecha or datetime.now(UTC).isoformat(),
            "desfase_pct": drift_pct or "",
        }

        rows.append(record)
        self._write_rows(rows)
        return str(self.csv_path), drift_pct
