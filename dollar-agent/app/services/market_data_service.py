from __future__ import annotations

import logging

from app.clients.market_data_client import MarketDataClient


logger = logging.getLogger(__name__)


class MarketDataService:
    def __init__(self, client: MarketDataClient) -> None:
        self.client = client

    def fetch_snapshot(self) -> tuple[dict[str, float | None], list[str]]:
        warnings: list[str] = []

        def safe_call(label: str, fn):
            try:
                return fn()
            except Exception as exc:
                logger.warning("market_data_fetch_failed %s: %s", label, exc)
                warnings.append(f"Failed to fetch {label}; continuing with partial data.")
                return None

        market_data = {
            "trm_current": safe_call("trm_current", self.client.get_trm_tradingview),
            "usd_cop": safe_call("usd_cop", self.client.get_usd_cop),
            "dxy": safe_call("dxy", self.client.get_dxy),
            "brent_oil": safe_call("brent_oil", self.client.get_brent_oil),
            "sp500": safe_call("sp500", self.client.get_sp500),
            "vix": safe_call("vix", self.client.get_vix),
        }

        if market_data.get("trm_current") is None and market_data.get("usd_cop") is not None:
            market_data["trm_current"] = market_data["usd_cop"]
            warnings.append("TradingView TRM unavailable; using usd_cop fallback.")

        missing = [key for key, value in market_data.items() if value is None]
        if missing:
            warnings.append(
                "Market fallbacks exhausted for: " + ", ".join(missing)
            )

        if len(missing) == len(market_data):
            market_data = {
                "trm_current": 4050.0,
                "usd_cop": 4050.0,
                "dxy": 104.0,
                "brent_oil": 78.0,
                "sp500": 5000.0,
                "vix": 19.0,
            }
            warnings.append(
                "Using proxy baseline market values due to unavailable public feeds."
            )

        return market_data, warnings
