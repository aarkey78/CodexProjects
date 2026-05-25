from __future__ import annotations

import pandas as pd

from agents.base import TradeSignal
from data.indicators import add_indicators


class BreakoutStrategy:
    """Simple high-of-range breakout strategy."""

    name = "breakout_strategy"

    def generate(self, symbol: str, candles: pd.DataFrame, lookback: int = 40) -> TradeSignal:
        enriched = add_indicators(candles)
        if len(enriched) < lookback + 1:
            return TradeSignal(symbol, "HOLD", 0.0, "Insufficient candles.", {})
        latest = enriched.iloc[-1]
        range_high = float(enriched.iloc[-lookback - 1 : -1]["high"].max())
        breakout = latest["close"] > range_high and latest.get("relative_volume", 0) > 2
        return TradeSignal(
            symbol=symbol,
            action="BUY" if breakout else "HOLD",
            confidence=0.72 if breakout else 0.35,
            reasoning="Range breakout with elevated volume." if breakout else "No breakout.",
            features={"range_high": range_high, "latest_price": float(latest["close"]), "relative_volume": float(latest.get("relative_volume", 0))},
        )

