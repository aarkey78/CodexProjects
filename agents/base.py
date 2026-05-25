from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Protocol


SignalAction = Literal["BUY", "SELL", "HOLD"]


@dataclass(slots=True)
class AgentResult:
    agent: str
    symbol: str
    score: float
    passed: bool
    reasoning: str
    features: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class TradeSignal:
    symbol: str
    action: SignalAction
    confidence: float
    reasoning: str
    features: dict[str, Any] = field(default_factory=dict)
    risk: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class TradingAgent(Protocol):
    name: str

    async def analyze(self, *args: Any, **kwargs: Any) -> AgentResult:
        ...

