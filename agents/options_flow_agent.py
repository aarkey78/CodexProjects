from __future__ import annotations

from typing import Any

from agents.base import AgentResult
from data.options_client import AlpacaOptionsClient, OptionsChainFilters, summarize_options_activity


class OptionsFlowAgent:
    """Scores options-chain activity and call/put imbalance."""

    name = "options_flow"

    def __init__(self, options_client: AlpacaOptionsClient | None = None) -> None:
        self.options_client = options_client

    async def analyze(
        self,
        symbol: str,
        chain: list[dict[str, Any]] | None = None,
        filters: OptionsChainFilters | None = None,
    ) -> AgentResult:
        if chain is None:
            if self.options_client is None:
                return AgentResult(
                    agent=self.name,
                    symbol=symbol,
                    score=0.0,
                    passed=False,
                    reasoning="Options client not configured.",
                    features={},
                )
            payload = await self.options_client.get_chain(symbol, filters)
            chain = payload["contracts"]
            summary = payload["summary"]
        else:
            summary = summarize_options_activity(chain)

        score = float(summary.get("top_unusual_activity_score") or 0.0) / 100
        flow_bias = summary.get("flow_bias", "neutral")
        passed = score >= 0.65 or flow_bias in {"call_heavy", "put_heavy"}
        return AgentResult(
            agent=self.name,
            symbol=symbol,
            score=score,
            passed=passed,
            reasoning=(
                f"Options activity score {score:.2f}; bias={flow_bias}; "
                f"top contract={summary.get('top_contract')}."
            ),
            features={**summary, "contracts_analyzed": len(chain)},
        )
