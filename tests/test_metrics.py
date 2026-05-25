from __future__ import annotations

import pandas as pd
import pytest

from backtesting.metrics import build_report, max_drawdown, win_rate


def test_metrics_report() -> None:
    equity = pd.Series([100_000, 101_000, 99_000, 104_000, 103_000])
    report = build_report(100_000, equity, [500, -250, 1000])

    assert report.total_return == pytest.approx(0.03)
    assert report.trades == 3
    assert win_rate([1, -1, 2]) == 2 / 3
    assert max_drawdown(equity) < 0
