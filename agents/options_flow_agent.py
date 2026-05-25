from __future__ import annotations

from agents.base import AgentResult


class OptionsFlowAgent:
    """Placeholder for unusual options flow integration."""

    name = "options_flow"

    async def analyze(self, symbol: str) -> AgentResult:
        return AgentResult(
            agent=self.name,
            symbol=symbol,
            score=0.5,
            passed=False,
            reasoning=(
                "Options flow provider not configured. Placeholder ready for sweep, block, "
                "put/call skew, IV rank, and expiration clustering signals."
            ),
            features={
                "provider": None,
                "unusual_sweeps": [],
                "premium_volume": 0,
                "put_call_ratio": None,
                "iv_rank": None,
            },
        )

