from __future__ import annotations

import pytest

from agents.options_flow_agent import OptionsFlowAgent
from config.settings import Settings
from data.options_client import (
    AlpacaOptionsClient,
    OptionsChainFilters,
    is_monthly_expiration,
    parse_option_symbol,
    summarize_options_activity,
)


def test_parse_option_symbol() -> None:
    parsed = parse_option_symbol("AAPL260605P00230000")

    assert parsed is not None
    assert parsed["root"] == "AAPL"
    assert parsed["option_type"] == "put"
    assert parsed["strike"] == 230.0
    assert parsed["expiration_date"].isoformat() == "2026-06-05"


def test_summarize_options_activity_bias() -> None:
    rows = [
        {"option_type": "call", "premium_proxy": 10_000.0, "activity_proxy": 100, "implied_volatility": 0.4, "contract_symbol": "CALL1", "unusual_activity_score": 80},
        {"option_type": "put", "premium_proxy": 2_000.0, "activity_proxy": 25, "implied_volatility": 0.3, "contract_symbol": "PUT1", "unusual_activity_score": 30},
    ]

    summary = summarize_options_activity(rows)

    assert summary["flow_bias"] == "call_heavy"
    assert summary["call_put_premium_ratio"] == 5.0
    assert summary["top_contract"] == "CALL1"
    assert "monthly_expiration_pressure_score" in summary


@pytest.mark.asyncio
async def test_options_client_mock_chain_filters() -> None:
    settings = Settings(
        alpaca_api_key=None,
        alpaca_secret_key=None,
        enable_mock_data=True,
        redis_url="",
    )
    payload = await AlpacaOptionsClient(settings).get_chain(
        "TEST",
        OptionsChainFilters(option_type="call", min_unusual_score=0, limit=3),
    )

    assert payload["symbol"] == "TEST"
    assert payload["contract_count"] <= 3
    assert all(contract["option_type"] == "call" for contract in payload["contracts"])
    assert "call_put_premium_ratio" in payload["summary"]


def test_is_monthly_expiration() -> None:
    assert is_monthly_expiration(parse_option_symbol("SPY260619C00600000")["expiration_date"]) is True
    assert is_monthly_expiration(parse_option_symbol("SPY260605C00600000")["expiration_date"]) is False


@pytest.mark.asyncio
async def test_options_flow_agent_scores_chain() -> None:
    chain = [
        {"option_type": "call", "premium_proxy": 12_000.0, "activity_proxy": 150, "implied_volatility": 0.5, "contract_symbol": "CALL1", "unusual_activity_score": 75},
        {"option_type": "put", "premium_proxy": 3_000.0, "activity_proxy": 30, "implied_volatility": 0.35, "contract_symbol": "PUT1", "unusual_activity_score": 25},
    ]

    result = await OptionsFlowAgent().analyze("TEST", chain)

    assert result.agent == "options_flow"
    assert result.passed is True
    assert result.features["flow_bias"] == "call_heavy"
