from __future__ import annotations

import pandas as pd

from agents.base import AgentResult
from data.indicators import add_indicators, detect_rsi_divergence


class TechnicalAnalysisAgent:
    """Computes and summarizes technical indicator state."""

    name = "technical"

    async def enrich(self, candles: pd.DataFrame) -> pd.DataFrame:
        return add_indicators(candles)

    async def analyze(self, symbol: str, candles: pd.DataFrame) -> AgentResult:
        enriched = add_indicators(candles)
        if enriched.empty:
            return AgentResult(self.name, symbol, 0.0, False, "No technical data available.")

        latest = enriched.iloc[-1]
        ema_stack = latest.get("ema_9", 0) > latest.get("ema_20", 0) > latest.get("ema_50", 0)
        above_vwap = latest.get("close", 0) > latest.get("vwap", float("inf"))
        rsi_value = float(latest.get("rsi", 0) or 0)
        macd_positive = latest.get("macd", 0) > latest.get("macd_signal", 0)
        divergence = detect_rsi_divergence(enriched)

        score = (
            0.30 * float(above_vwap)
            + 0.30 * float(latest.get("ema_9", 0) > latest.get("ema_20", 0))
            + 0.20 * float(55 <= rsi_value <= 75)
            + 0.15 * float(macd_positive)
            - 0.15 * float(divergence)
            + 0.05 * float(ema_stack)
        )
        features = {
            "close": float(latest.get("close", 0)),
            "vwap": float(latest.get("vwap", 0)),
            "ema_9": float(latest.get("ema_9", 0)),
            "ema_20": float(latest.get("ema_20", 0)),
            "ema_50": float(latest.get("ema_50", 0)),
            "ema_200": float(latest.get("ema_200", 0)),
            "rsi": rsi_value,
            "macd": float(latest.get("macd", 0)),
            "macd_signal": float(latest.get("macd_signal", 0)),
            "atr": float(latest.get("atr", 0) or 0),
            "bb_upper": float(latest.get("bb_upper", 0) or 0),
            "bb_lower": float(latest.get("bb_lower", 0) or 0),
            "rsi_divergence": divergence,
        }
        return AgentResult(
            agent=self.name,
            symbol=symbol,
            score=max(min(score, 1.0), 0.0),
            passed=score >= 0.65,
            reasoning=(
                f"Technical score {score:.2f}: above_vwap={above_vwap}, "
                f"ema9_gt_ema20={latest.get('ema_9', 0) > latest.get('ema_20', 0)}, "
                f"rsi={rsi_value:.1f}, macd_positive={macd_positive}."
            ),
            features=features,
        )

