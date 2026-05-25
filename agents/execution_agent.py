from __future__ import annotations

from agents.base import AgentResult, TradeSignal
from data.alpaca_client import AlpacaTradingClient, BrokerOrder


class ExecutionAgent:
    """Executes approved trade signals through Alpaca or mock mode."""

    name = "execution"

    def __init__(self, broker: AlpacaTradingClient) -> None:
        self.broker = broker

    async def analyze(self, signal: TradeSignal, execute: bool = False) -> AgentResult:
        if signal.action == "HOLD":
            return AgentResult(self.name, signal.symbol, 0.0, False, "No execution for HOLD signal.")

        quantity = int(signal.risk.get("quantity", 0))
        approved = bool(signal.risk.get("approved", False))
        if not approved or quantity <= 0:
            return AgentResult(self.name, signal.symbol, 0.0, False, "Risk plan not approved.")

        if not execute:
            return AgentResult(
                self.name,
                signal.symbol,
                1.0,
                True,
                "Execution dry run only; order not submitted.",
                {"quantity": quantity, "side": signal.action.lower()},
            )

        side = "buy" if signal.action == "BUY" else "sell"
        order = BrokerOrder(symbol=signal.symbol, qty=quantity, side=side)
        submitted = await self.broker.submit_order(order)
        return AgentResult(
            agent=self.name,
            symbol=signal.symbol,
            score=1.0,
            passed=True,
            reasoning=f"Submitted {side} market order for {quantity} shares.",
            features={"order": submitted},
        )

