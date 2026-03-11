from __future__ import annotations

import csv
from pathlib import Path

from app.utils.runtime_paths import project_root


class ForecastLearningService:
    def __init__(self) -> None:
        self.csv_path = project_root() / "data" / "history" / "forecast_tracking.csv"

    def calibration_factor(self) -> tuple[float, str | None, int]:
        if not self.csv_path.exists():
            return 1.0, None, 0

        drifts: list[float] = []
        with self.csv_path.open("r", newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                raw = (row.get("desfase_pct") or "").strip()
                if not raw:
                    continue
                try:
                    drift = float(raw)
                except ValueError:
                    continue
                if drift < -10.0 or drift > 10.0:
                    continue
                drifts.append(drift)

        if len(drifts) < 1:
            return 1.0, None, len(drifts)

        recent = drifts[-20:]
        mean_drift_pct = sum(recent) / len(recent)

        # Drift definition: (actual - previous_forecast) / previous_forecast.
        # Positive drift means previous forecast was too low; negative means too high.
        factor = 1.0 + (mean_drift_pct / 100.0)
        factor = max(0.70, min(1.30, factor))

        note = f"learning_bias_mean={mean_drift_pct:.4f}%"
        return factor, note, len(recent)

    def _recent_mape(self, max_samples: int = 20) -> list[float]:
        if not self.csv_path.exists():
            return []

        values: list[float] = []
        with self.csv_path.open("r", newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                try:
                    actual = float((row.get("trm_actual") or "").strip())
                    forecast = float((row.get("forecast") or "").strip())
                except ValueError:
                    continue

                if actual == 0:
                    continue
                # Guardrail for malformed rows from parser issues.
                if actual < 1000 or forecast < 1000:
                    continue

                mape = abs((actual - forecast) / actual) * 100.0
                values.append(mape)

        return values[-max_samples:]

    def adjust_confidence(self, base_confidence: str) -> tuple[str, str | None]:
        mape_values = self._recent_mape()
        if len(mape_values) < 2:
            return base_confidence, None

        mean_mape = sum(mape_values) / len(mape_values)
        order = ["low", "medium", "high"]
        current = base_confidence.lower()
        if current not in order:
            current = "medium"

        idx = order.index(current)
        # Improve confidence if historical error is consistently small.
        if mean_mape <= 0.35 and idx < len(order) - 1:
            adjusted = order[idx + 1]
            note = f"confidence adjusted {current}->{adjusted} from historical MAPE={mean_mape:.4f}% ({len(mape_values)} samples)"
            return adjusted, note

        # Reduce confidence if historical error is high.
        if mean_mape >= 1.20 and idx > 0:
            adjusted = order[idx - 1]
            note = f"confidence adjusted {current}->{adjusted} from historical MAPE={mean_mape:.4f}% ({len(mape_values)} samples)"
            return adjusted, note

        note = f"historical MAPE check={mean_mape:.4f}% ({len(mape_values)} samples), confidence unchanged"
        return current, note
