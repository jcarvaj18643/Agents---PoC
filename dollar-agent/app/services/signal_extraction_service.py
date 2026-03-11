from __future__ import annotations


class SignalExtractionService:
    def _append_market_signals(
        self,
        signals: list[dict[str, str | float]],
        market_data: dict[str, float | None],
    ) -> None:
        usd_cop = market_data.get("usd_cop")
        dxy = market_data.get("dxy")
        brent = market_data.get("brent_oil")
        vix = market_data.get("vix")

        if dxy is not None:
            direction = "up" if dxy >= 104 else "down"
            signals.append(
                {
                    "name": "DXY context",
                    "direction": direction,
                    "weight": 0.9,
                    "source": "market_data",
                    "rationale": "Higher DXY tends to support USD strength versus EM FX.",
                }
            )

        if brent is not None:
            direction = "down" if brent >= 80 else "up"
            signals.append(
                {
                    "name": "Oil context",
                    "direction": direction,
                    "weight": 0.7,
                    "source": "market_data",
                    "rationale": "Higher oil usually supports Colombia's external balance and COP.",
                }
            )

        if vix is not None:
            direction = "up" if vix >= 20 else "down"
            signals.append(
                {
                    "name": "Risk sentiment via VIX",
                    "direction": direction,
                    "weight": 0.8,
                    "source": "market_data",
                    "rationale": "Higher VIX often pressures EM currencies and supports USD/COP up.",
                }
            )

        if usd_cop is not None:
            signals.append(
                {
                    "name": "Spot USD/COP reference",
                    "direction": "mixed",
                    "weight": 0.4,
                    "source": "market_data",
                    "rationale": f"Current spot reference observed at {usd_cop:.2f}.",
                }
            )

    def _append_macro_signals(
        self,
        signals: list[dict[str, str | float]],
        macro_data: dict[str, str],
    ) -> None:
        risk_sentiment = macro_data.get("risk_sentiment", "mixed")
        if risk_sentiment == "risk_off":
            signals.append(
                {
                    "name": "Macro risk-off regime",
                    "direction": "up",
                    "weight": 0.75,
                    "source": "macro",
                    "rationale": "Risk-off regimes typically support USD versus EMFX.",
                }
            )
        elif risk_sentiment == "risk_on":
            signals.append(
                {
                    "name": "Macro risk-on regime",
                    "direction": "down",
                    "weight": 0.7,
                    "source": "macro",
                    "rationale": "Risk-on regimes tend to support EMFX and reduce USD demand.",
                }
            )

        fed_narrative = str(macro_data.get("fed_narrative", ""))
        banrep_narrative = str(macro_data.get("banrep_narrative", ""))
        inflation_narrative = str(macro_data.get("colombia_inflation_narrative", ""))

        if "higher_for_longer" in fed_narrative and "easing" in banrep_narrative:
            signals.append(
                {
                    "name": "Rate differential (Fed vs BanRep)",
                    "direction": "up",
                    "weight": 0.95,
                    "source": "macro",
                    "rationale": "Hawkish Fed with BanRep easing tends to favor USD over COP.",
                }
            )

        if "sticky" in inflation_narrative:
            signals.append(
                {
                    "name": "Colombia inflation stickiness",
                    "direction": "up",
                    "weight": 0.6,
                    "source": "macro",
                    "rationale": "Sticky inflation can delay local easing confidence and increase FX volatility.",
                }
            )

    def _append_news_signals(
        self,
        signals: list[dict[str, str | float]],
        news_items: list[dict[str, str]],
    ) -> None:
        if not news_items:
            return

        up_keywords = (
            "fed",
            "hawkish",
            "risk-off",
            "geopolitical",
            "inflation",
            "banrep cut",
        )
        down_keywords = (
            "oil rises",
            "brent rises",
            "risk-on",
            "capital inflows",
            "cop strengthens",
            "peso gains",
        )

        up_hits = 0
        down_hits = 0
        for item in news_items:
            text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
            up_hits += sum(1 for key in up_keywords if key in text)
            down_hits += sum(1 for key in down_keywords if key in text)

        signals.append(
            {
                "name": "News flow momentum",
                "direction": "mixed",
                "weight": 0.5,
                "source": "news",
                "rationale": f"{len(news_items)} potentially relevant market news items detected.",
            }
        )

        if up_hits > down_hits:
            signals.append(
                {
                    "name": "News macro tone balance",
                    "direction": "up",
                    "weight": 0.65,
                    "source": "news",
                    "rationale": f"Recent headlines show more USD-supportive macro tone ({up_hits} vs {down_hits} keyword hits).",
                }
            )
        elif down_hits > up_hits:
            signals.append(
                {
                    "name": "News macro tone balance",
                    "direction": "down",
                    "weight": 0.65,
                    "source": "news",
                    "rationale": f"Recent headlines show more COP-supportive macro tone ({down_hits} vs {up_hits} keyword hits).",
                }
            )

    def extract(
        self,
        market_data: dict[str, float | None],
        macro_data: dict[str, str],
        news_items: list[dict[str, str]],
    ) -> list[dict[str, str | float]]:
        signals: list[dict[str, str | float]] = []

        self._append_market_signals(signals, market_data)
        self._append_macro_signals(signals, macro_data)
        self._append_news_signals(signals, news_items)

        if not signals:
            signals.append(
                {
                    "name": "Insufficient market inputs",
                    "direction": "mixed",
                    "weight": 0.2,
                    "source": "fallback",
                    "rationale": "Not enough high-quality inputs; directional view remains uncertain.",
                }
            )

        return signals
