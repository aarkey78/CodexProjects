from __future__ import annotations

from agents.risk_agent import RiskAgent
from config.settings import Settings


def test_risk_plan_sizes_position_and_sets_targets() -> None:
    settings = Settings(enable_mock_data=True)
    plan = RiskAgent(settings).build_plan(entry_price=100.0, atr=2.0, account_equity=100_000, confidence=0.8)

    assert plan.quantity > 0
    assert plan.stop_loss < plan.entry_price
    assert plan.profit_target > plan.entry_price
    assert plan.reward_to_risk >= 1.5
    assert plan.approved is True

