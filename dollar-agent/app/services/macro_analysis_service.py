from __future__ import annotations

from app.clients.macro_data_client import MacroDataClient


class MacroAnalysisService:
    def __init__(self, client: MacroDataClient) -> None:
        self.client = client

    def analyze(self, market_data: dict[str, float | None]) -> dict[str, str]:
        macro = self.client.get_macro_context()

        risk_sentiment = "mixed"
        vix = market_data.get("vix")
        sp500 = market_data.get("sp500")
        if vix is not None and vix > 22:
            risk_sentiment = "risk_off"
        elif sp500 is not None and sp500 > 5000:
            risk_sentiment = "risk_on"

        macro["risk_sentiment"] = risk_sentiment
        return macro
