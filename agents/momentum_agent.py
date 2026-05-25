from __future__ import annotations

import pandas as pd

from agents.base import AgentResult
from data.indicators import add_indicators


class MomentumAgent:
    """Ranks stocks by relative volume, VWAP position, breakout, and acceleration."""

    name = "momentum"

    async def analyze(self, symbol: str, intraday_candles: pd.DataFrame) -> AgentResult:
        candles = add_indicators(intraday_candles)
        if len(candles) < 30:
            return AgentResult(self.name, symbol, 0.0, False, "Not enough intraday candles.")

        latest = candles.iloc[-1]
        recent = candles.tail(6)
        previous_window = candles.iloc[:-1].tail(40)
        relative_volume = float(latest.get("relative_volume", 0) or 0)
        above_vwap = latest["close"] > latest.get("vwap", float("inf"))
        breakout_level = float(previous_window["high"].max())
        breaking_high = latest["close"] > breakout_level
        returns = recent["close"].pct_change().dropna()
        acceleration = bool(len(returns) >= 3 and returns.tail(3).is_monotonic_increasing and returns.iloc[-1] > 0)

        score = (
            0.35 * min(relative_volume / 3.0, 1.5)
            + 0.25 * float(above_vwap)
            + 0.25 * float(breaking_high)
            + 0.15 * float(acceleration)
        )
        features = {
            "relative_volume": relative_volume,
            "above_vwap": above_vwap,
            "breakout_level": breakout_level,
            "breaking_premarket_high": breaking_high,
            "five_min_acceleration": acceleration,
            "latest_price": float(latest["close"]),
            "vwap": float(latest.get("vwap", 0)),
        }
        return AgentResult(
            agent=self.name,
            symbol=symbol,
            score=max(min(score, 1.0), 0.0),
            passed=relative_volume > 2 and above_vwap and (breaking_high or acceleration),
            reasoning=(
                f"Momentum score {score:.2f}: rel_vol={relative_volume:.2f}, "
                f"above_vwap={above_vwap}, breakout={breaking_high}, acceleration={acceleration}."
            ),
            features=features,
        )

    async def rank(self, candles_by_symbol: dict[str, pd.DataFrame]) -> list[AgentResult]:
        results = [await self.analyze(symbol, candles) for symbol, candles in candles_by_symbol.items()]
        return sorted(results, key=lambda item: item.score, reverse=True)

