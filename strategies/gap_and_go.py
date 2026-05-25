from __future__ import annotations

import pandas as pd

from agents.base import TradeSignal
from data.indicators import add_indicators


class GapAndGoStrategy:
    """Premarket gap continuation placeholder strategy."""

    name = "gap_and_go"

    def generate(self, symbol: str, intraday: pd.DataFrame, prior_close: float | None = None) -> TradeSignal:
        candles = add_indicators(intraday)
        if candles.empty or prior_close is None:
            return TradeSignal(symbol, "HOLD", 0.0, "Missing prior close or intraday data.", {})
        first = candles.iloc[0]
        latest = candles.iloc[-1]
        gap_pct = (first["open"] - prior_close) / prior_close
        holds_vwap = latest["close"] > latest.get("vwap", float("inf"))
        continuation = gap_pct > 0.04 and holds_vwap and latest.get("relative_volume", 0) > 2
        return TradeSignal(
            symbol=symbol,
            action="BUY" if continuation else "HOLD",
            confidence=0.7 if continuation else 0.3,
            reasoning="Gap-and-go continuation confirmed." if continuation else "Gap setup not confirmed.",
            features={"gap_pct": float(gap_pct), "above_vwap": bool(holds_vwap), "latest_price": float(latest["close"])},
        )

