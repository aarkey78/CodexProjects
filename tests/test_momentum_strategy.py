from __future__ import annotations

from agents.base import AgentResult
from strategies.momentum_strategy import MomentumStrategy


def test_momentum_strategy_buy_signal() -> None:
    momentum = AgentResult("momentum", "NVDA", 0.95, True, "", {"relative_volume": 4, "above_vwap": True, "latest_price": 100})
    volume = AgentResult("volume", "NVDA", 0.8, True, "", {"spike_vs_10_day": 3})
    technical = AgentResult("technical", "NVDA", 0.9, True, "", {"ema_9": 105, "ema_20": 100, "rsi": 62, "atr": 2})
    sentiment = AgentResult("sentiment", "NVDA", 0.85, True, "", {"sentiment_score": 0.8})

    signal = MomentumStrategy().generate("NVDA", momentum, volume, technical, sentiment)

    assert signal.action == "BUY"
    assert signal.confidence > 0.8

