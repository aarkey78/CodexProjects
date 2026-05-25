from __future__ import annotations

from agents.base import AgentResult, TradeSignal
from data.indicators import detect_rsi_divergence


class MomentumStrategy:
    """Converts agent outputs into BUY/SELL/HOLD signals."""

    name = "momentum_strategy"

    def generate(
        self,
        symbol: str,
        momentum: AgentResult,
        volume: AgentResult,
        technical: AgentResult,
        sentiment: AgentResult,
        market_trend_bullish: bool = True,
    ) -> TradeSignal:
        features = {
            **momentum.features,
            **volume.features,
            **technical.features,
            "sentiment_score": sentiment.features.get("sentiment_score", sentiment.score),
            "market_trend_bullish": market_trend_bullish,
        }

        buy_conditions = [
            features.get("relative_volume", 0) > 3,
            bool(features.get("above_vwap")),
            features.get("ema_9", 0) > features.get("ema_20", 0),
            55 <= features.get("rsi", 0) <= 75,
            features.get("sentiment_score", 0) > 0.7,
            market_trend_bullish,
        ]

        sell_conditions = [
            momentum.score < 0.35,
            features.get("spike_vs_10_day", 1) < 0.8,
            bool(features.get("rsi_divergence")),
        ]

        if all(buy_conditions):
            confidence = min(
                1.0,
                0.25 * momentum.score
                + 0.20 * volume.score
                + 0.30 * technical.score
                + 0.25 * sentiment.score,
            )
            return TradeSignal(
                symbol=symbol,
                action="BUY",
                confidence=confidence,
                reasoning=(
                    "BUY: relative volume, VWAP, EMA trend, RSI window, sentiment, "
                    "and market trend all aligned."
                ),
                features=features,
            )

        if any(sell_conditions):
            confidence = min(1.0, 0.45 + 0.25 * bool(features.get("rsi_divergence")) + 0.15 * (momentum.score < 0.35))
            return TradeSignal(
                symbol=symbol,
                action="SELL",
                confidence=confidence,
                reasoning="SELL: momentum weakened, volume declined, or RSI divergence appeared.",
                features=features,
            )

        confidence = (momentum.score + volume.score + technical.score + sentiment.score) / 4
        return TradeSignal(
            symbol=symbol,
            action="HOLD",
            confidence=confidence,
            reasoning="HOLD: setup is incomplete or conflicting.",
            features=features,
        )

    @staticmethod
    def stop_triggered(latest_price: float, stop_loss: float) -> bool:
        return latest_price <= stop_loss


def generate_sell_from_candles(symbol: str, candles, existing_stop: float | None = None) -> TradeSignal:
    latest = candles.iloc[-1]
    stop_hit = existing_stop is not None and latest["close"] <= existing_stop
    divergence = detect_rsi_divergence(candles)
    action = "SELL" if stop_hit or divergence else "HOLD"
    return TradeSignal(
        symbol=symbol,
        action=action,
        confidence=0.8 if stop_hit else 0.55,
        reasoning="Stop loss triggered." if stop_hit else "RSI divergence detected." if divergence else "No sell trigger.",
        features={"latest_price": float(latest["close"]), "stop_loss": existing_stop, "rsi_divergence": divergence},
    )

