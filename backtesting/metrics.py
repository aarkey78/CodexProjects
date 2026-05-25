from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd


@dataclass(slots=True)
class PerformanceReport:
    total_return: float
    sharpe_ratio: float
    win_rate: float
    max_drawdown: float
    trades: int
    profit_factor: float

    def as_dict(self) -> dict[str, float | int]:
        return {
            "total_return": self.total_return,
            "sharpe_ratio": self.sharpe_ratio,
            "win_rate": self.win_rate,
            "max_drawdown": self.max_drawdown,
            "trades": self.trades,
            "profit_factor": self.profit_factor,
        }


def sharpe_ratio(equity_curve: pd.Series, periods_per_year: int = 252) -> float:
    returns = equity_curve.pct_change().dropna()
    if returns.empty or returns.std() == 0:
        return 0.0
    return float(math.sqrt(periods_per_year) * returns.mean() / returns.std())


def max_drawdown(equity_curve: pd.Series) -> float:
    if equity_curve.empty:
        return 0.0
    running_max = equity_curve.cummax()
    drawdown = equity_curve / running_max - 1
    return float(drawdown.min())


def win_rate(trade_pnls: list[float]) -> float:
    if not trade_pnls:
        return 0.0
    return sum(1 for pnl in trade_pnls if pnl > 0) / len(trade_pnls)


def profit_factor(trade_pnls: list[float]) -> float:
    gains = sum(pnl for pnl in trade_pnls if pnl > 0)
    losses = abs(sum(pnl for pnl in trade_pnls if pnl < 0))
    if losses == 0:
        return float("inf") if gains > 0 else 0.0
    return gains / losses


def build_report(initial_capital: float, equity_curve: pd.Series, trade_pnls: list[float]) -> PerformanceReport:
    final_equity = float(equity_curve.iloc[-1]) if not equity_curve.empty else initial_capital
    return PerformanceReport(
        total_return=(final_equity / initial_capital) - 1,
        sharpe_ratio=sharpe_ratio(equity_curve),
        win_rate=win_rate(trade_pnls),
        max_drawdown=max_drawdown(equity_curve),
        trades=len(trade_pnls),
        profit_factor=profit_factor(trade_pnls),
    )

