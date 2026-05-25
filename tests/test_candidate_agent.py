from __future__ import annotations

from agents.base import AgentResult
from agents.candidate_agent import score_options_momentum_candidate


def test_score_options_momentum_candidate_day_trade_long() -> None:
    momentum = AgentResult(
        "momentum",
        "NVDA",
        0.9,
        True,
        "",
        {"relative_volume": 3.4, "above_vwap": True, "latest_price": 150.0},
    )
    volume = AgentResult("volume", "NVDA", 0.8, True, "", {})
    technical = AgentResult(
        "technical",
        "NVDA",
        0.9,
        True,
        "",
        {
            "rsi": 64,
            "vwap": 148,
            "ema_9": 151,
            "ema_20": 149,
            "macd": 1.2,
            "macd_signal": 0.7,
        },
    )
    options_payload = {
        "summary": {
            "flow_bias": "call_heavy",
            "monthly_expiration_pressure": "high",
            "monthly_expiration_pressure_score": 85,
            "top_contract": "NVDA260619C00150000",
            "top_unusual_activity_score": 90,
            "call_put_premium_ratio": 2.0,
            "call_put_open_interest_ratio": 1.7,
            "avg_volume_open_interest_ratio": 0.45,
            "total_open_interest": 25_000,
            "avg_iv": 0.55,
        },
        "contracts": [
            {
                "contract_symbol": "NVDA260619C00150000",
                "option_type": "call",
                "expiration_date": "2026-06-19",
                "strike": 150,
                "mid": 4.2,
                "implied_volatility": 0.55,
                "delta": 0.52,
                "gamma": 0.04,
                "open_interest": 12_000,
                "volume_open_interest_ratio": 0.6,
                "premium_proxy": 500_000,
                "unusual_activity_score": 90,
                "spread_pct": 0.04,
            }
        ],
    }

    candidate = score_options_momentum_candidate("NVDA", momentum, volume, technical, options_payload)

    assert candidate.setup == "DAY_TRADE_LONG"
    assert candidate.final_score >= 75
    assert candidate.options_bias == "call_heavy"
    assert candidate.technical_confirmation is True

