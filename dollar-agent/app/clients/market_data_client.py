from __future__ import annotations

import csv
from io import StringIO

import requests

from app.config import settings


class MarketDataClient:
    BASE = "https://stooq.com/q/l/"
    YAHOO_QUOTE_API = "https://query1.finance.yahoo.com/v7/finance/quote"
    EXCHANGE_RATE_HOST = "https://api.exchangerate.host/convert"
    FRED_SERIES_API = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    TRADINGVIEW_SCAN_API = "https://scanner.tradingview.com/forex/scan"

    def _fetch_stooq_close(self, symbol: str) -> float | None:
        params = {"s": symbol, "i": "d"}
        response = requests.get(
            self.BASE,
            params=params,
            timeout=settings.request_timeout_seconds,
        )
        response.raise_for_status()

        rows = list(csv.DictReader(StringIO(response.text)))
        if not rows:
            return None

        close_value = rows[0].get("Close")
        if not close_value or close_value in {"N/D", "0"}:
            return None

        try:
            return float(close_value)
        except ValueError:
            return None

    def _fetch_yahoo_quote(self, symbol: str) -> float | None:
        response = requests.get(
            self.YAHOO_QUOTE_API,
            params={"symbols": symbol},
            timeout=settings.request_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()

        quote_response = payload.get("quoteResponse", {})
        result = quote_response.get("result", [])
        if not result:
            return None

        value = result[0].get("regularMarketPrice")
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _fetch_exchangerate_usd_cop(self) -> float | None:
        response = requests.get(
            self.EXCHANGE_RATE_HOST,
            params={"from": "USD", "to": "COP", "amount": 1},
            timeout=settings.request_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()

        result = payload.get("result")
        if result is None:
            return None

        try:
            return float(result)
        except (TypeError, ValueError):
            return None

    def _first_available(self, resolvers: list) -> float | None:
        for resolver in resolvers:
            try:
                value = resolver()
            except Exception:
                continue
            if value is not None:
                return value
        return None

    def _fetch_fred_latest(self, series_id: str) -> float | None:
        response = requests.get(
            self.FRED_SERIES_API,
            params={"id": series_id},
            timeout=settings.request_timeout_seconds,
        )
        response.raise_for_status()

        rows = list(csv.DictReader(StringIO(response.text)))
        if not rows:
            return None

        value: float | None = None
        for row in rows:
            raw = str(row.get(series_id, "")).strip()
            if not raw or raw == ".":
                continue
            try:
                value = float(raw)
            except ValueError:
                continue

        return value

    def _fetch_tradingview_usdcop(self) -> float | None:
        payload = {
            "symbols": {
                "tickers": ["FX_IDC:USDCOP"],
                "query": {"types": []},
            },
            "columns": ["close"],
        }

        response = requests.post(
            self.TRADINGVIEW_SCAN_API,
            json=payload,
            timeout=settings.request_timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()

        rows = data.get("data", []) if isinstance(data, dict) else []
        if not rows:
            return None

        first = rows[0] if isinstance(rows[0], dict) else {}
        values = first.get("d", []) if isinstance(first, dict) else []
        if not values:
            return None

        try:
            return float(values[0])
        except (TypeError, ValueError):
            return None

    def get_usd_cop(self) -> float | None:
        return self._first_available(
            [
                self._fetch_tradingview_usdcop,
                lambda: self._fetch_stooq_close("usdcop"),
                lambda: self._fetch_yahoo_quote("USDCOP=X"),
                self._fetch_exchangerate_usd_cop,
                lambda: self._fetch_fred_latest("DEXCOUS"),
            ]
        )

    def get_trm_tradingview(self) -> float | None:
        return self._fetch_tradingview_usdcop()

    def get_dxy(self) -> float | None:
        return self._first_available(
            [
                lambda: self._fetch_stooq_close("dx-y.nyb"),
                lambda: self._fetch_yahoo_quote("DX-Y.NYB"),
                lambda: self._fetch_fred_latest("DTWEXBGS"),
            ]
        )

    def get_brent_oil(self) -> float | None:
        return self._first_available(
            [
                lambda: self._fetch_stooq_close("brent"),
                lambda: self._fetch_yahoo_quote("BZ=F"),
                lambda: self._fetch_fred_latest("DCOILBRENTEU"),
            ]
        )

    def get_sp500(self) -> float | None:
        return self._first_available(
            [
                lambda: self._fetch_stooq_close("spx"),
                lambda: self._fetch_yahoo_quote("^GSPC"),
                lambda: self._fetch_fred_latest("SP500"),
            ]
        )

    def get_vix(self) -> float | None:
        return self._first_available(
            [
                lambda: self._fetch_stooq_close("vix"),
                lambda: self._fetch_yahoo_quote("^VIX"),
                lambda: self._fetch_fred_latest("VIXCLS"),
            ]
        )
