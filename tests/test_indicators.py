from __future__ import annotations

import pandas as pd

from data.indicators import add_indicators


def test_add_indicators_adds_required_columns() -> None:
    index = pd.date_range("2025-01-01", periods=260, freq="D")
    close = pd.Series(range(100, 360), index=index, dtype=float)
    df = pd.DataFrame(
        {
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": [1_000_000 + idx * 1000 for idx in range(len(index))],
        },
        index=index,
    )

    enriched = add_indicators(df)

    for column in ["vwap", "ema_9", "ema_20", "ema_50", "ema_200", "rsi", "macd", "atr", "bb_upper", "relative_volume"]:
        assert column in enriched.columns
    assert enriched["ema_9"].iloc[-1] > enriched["ema_20"].iloc[-1]
    assert enriched["vwap"].notna().all()

