from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agents.base import AgentResult, TradeSignal


class JournalAgent:
    """Stores signals, trades, market context, and AI reasoning."""

    name = "journal"

    def __init__(self, journal_path: str = "logs/trade_journal.jsonl") -> None:
        self.journal_path = Path(journal_path)
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)

    async def record_signal(
        self,
        signal: TradeSignal,
        agent_results: list[AgentResult],
        execution: dict[str, Any] | None = None,
        screenshot_path: str | None = None,
    ) -> AgentResult:
        payload = {
            "symbol": signal.symbol,
            "action": signal.action,
            "confidence": signal.confidence,
            "reasoning": signal.reasoning,
            "features": signal.features,
            "risk": signal.risk,
            "execution": execution,
            "market_conditions": [result.features for result in agent_results],
            "agent_reasoning": [result.reasoning for result in agent_results],
            "screenshot_path": screenshot_path,
            "created_at": signal.created_at.isoformat(),
        }
        with self.journal_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, default=str) + "\n")

        return AgentResult(
            agent=self.name,
            symbol=signal.symbol,
            score=1.0,
            passed=True,
            reasoning=f"Signal journaled to {self.journal_path}.",
            features={"journal_path": str(self.journal_path)},
        )

