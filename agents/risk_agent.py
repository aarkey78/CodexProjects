from __future__ import annotations

from dataclasses import dataclass

from agents.base import AgentResult, TradeSignal
from config.settings import Settings


@dataclass(slots=True)
class RiskPlan:
    entry_price: float
    stop_loss: float
    profit_target: float
    quantity: int
    risk_per_share: float
    total_risk: float
    reward_to_risk: float
    approved: bool

    def as_dict(self) -> dict[str, float | int | bool]:
        return {
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "profit_target": self.profit_target,
            "quantity": self.quantity,
            "risk_per_share": self.risk_per_share,
            "total_risk": self.total_risk,
            "reward_to_risk": self.reward_to_risk,
            "approved": self.approved,
        }


class RiskAgent:
    """Creates position sizing, stop, target, and daily risk guardrails."""

    name = "risk"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def build_plan(
        self,
        entry_price: float,
        atr: float,
        account_equity: float | None = None,
        confidence: float = 0.5,
    ) -> RiskPlan:
        equity = account_equity or self.settings.default_account_equity
        max_position_risk = equity * self.settings.max_position_risk_pct * max(confidence, 0.25)
        max_daily_risk = equity * self.settings.max_daily_risk_pct
        stop_distance = max(atr * 1.5, entry_price * 0.015)
        stop_loss = entry_price - stop_distance
        profit_target = entry_price + stop_distance * 2.0
        quantity = int(max_position_risk // stop_distance) if stop_distance > 0 else 0
        total_risk = quantity * stop_distance
        reward_to_risk = (profit_target - entry_price) / stop_distance if stop_distance else 0.0
        approved = quantity > 0 and total_risk <= max_daily_risk and reward_to_risk >= 1.5
        return RiskPlan(
            entry_price=round(entry_price, 2),
            stop_loss=round(stop_loss, 2),
            profit_target=round(profit_target, 2),
            quantity=quantity,
            risk_per_share=round(stop_distance, 2),
            total_risk=round(total_risk, 2),
            reward_to_risk=round(reward_to_risk, 2),
            approved=approved,
        )

    async def analyze(self, signal: TradeSignal, account_equity: float | None = None) -> AgentResult:
        entry = float(signal.features.get("latest_price") or signal.features.get("close") or 0)
        atr = float(signal.features.get("atr") or entry * 0.02)
        plan = self.build_plan(entry, atr, account_equity, signal.confidence)
        signal.risk.update(plan.as_dict())
        return AgentResult(
            agent=self.name,
            symbol=signal.symbol,
            score=1.0 if plan.approved else 0.0,
            passed=plan.approved,
            reasoning=(
                f"Risk plan quantity={plan.quantity}, stop={plan.stop_loss}, "
                f"target={plan.profit_target}, R/R={plan.reward_to_risk}."
            ),
            features=plan.as_dict(),
        )

