from __future__ import annotations

import pandas as pd

from agents.base import AgentResult
from data.indicators import add_indicators


class VolumeAgent:
    """Detects unusual volume spikes and accumulation patterns."""

    name = "volume"

    async def analyze(self, symbol: str, candles: pd.DataFrame) -> AgentResult:
        enriched = add_indicators(candles)
        if len(enriched) < 30:
            return AgentResult(self.name, symbol, 0.0, False, "Not enough volume history.")

        latest = enriched.iloc[-1]
        volume = float(latest["volume"])
        avg_10 = float(enriched["volume"].tail(10).mean())
        avg_30 = float(enriched["volume"].tail(30).mean())
        spike_10 = volume / avg_10 if avg_10 else 0.0
        spike_30 = volume / avg_30 if avg_30 else 0.0
        last_8 = enriched.tail(8)
        accumulation_bars = ((last_8["close"] > last_8["open"]) & (last_8["volume"] > avg_30)).sum()
        accumulation = bool(accumulation_bars >= 4 and last_8["close"].iloc[-1] > last_8["close"].iloc[0])

        score = 0.45 * min(spike_10 / 2.0, 1.3) + 0.35 * min(spike_30 / 2.0, 1.3) + 0.20 * float(accumulation)
        features = {
            "volume": volume,
            "avg_volume_10": avg_10,
            "avg_volume_30": avg_30,
            "spike_vs_10_day": spike_10,
            "spike_vs_30_day": spike_30,
            "institutional_accumulation": accumulation,
            "accumulation_bars": int(accumulation_bars),
        }
        return AgentResult(
            agent=self.name,
            symbol=symbol,
            score=max(min(score, 1.0), 0.0),
            passed=spike_10 > 2 or spike_30 > 2 or accumulation,
            reasoning=(
                f"Volume score {score:.2f}: spike10={spike_10:.2f}, "
                f"spike30={spike_30:.2f}, accumulation={accumulation}."
            ),
            features=features,
        )

