from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from backtesting.metrics import PerformanceReport, build_report
from data.indicators import add_indicators, detect_rsi_divergence


@dataclass(slots=True)
class BacktestConfig:
    initial_capital: float = 100_000.0
    risk_per_trade_pct: float = 0.005
    commission_per_share: float = 0.0
    slippage_bps: float = 2.0
    relative_volume_threshold: float = 3.0
    stop_atr_multiple: float = 1.5
    target_r_multiple: float = 2.0


@dataclass(slots=True)
class BacktestTrade:
    symbol: str
    entry_time: str
    exit_time: str | None
    entry_price: float
    exit_price: float | None
    quantity: int
    pnl: float | None = None
    reason: str | None = None


@dataclass(slots=True)
class BacktestResult:
    equity_curve: pd.Series
    trades: list[BacktestTrade] = field(default_factory=list)
    report: PerformanceReport | None = None


class BacktestEngine:
    """Event-driven long-only engine for the core momentum rule set."""

    def __init__(self, config: BacktestConfig | None = None) -> None:
        self.config = config or BacktestConfig()

    def run(self, symbol: str, candles: pd.DataFrame) -> BacktestResult:
        data = add_indicators(candles)
        if len(data) < 60:
            equity = pd.Series([self.config.initial_capital], index=[pd.Timestamp.utcnow()])
            return BacktestResult(equity_curve=equity, report=build_report(self.config.initial_capital, equity, []))

        cash = self.config.initial_capital
        position_qty = 0
        entry_price = 0.0
        stop_loss = 0.0
        target = 0.0
        open_trade: BacktestTrade | None = None
        trades: list[BacktestTrade] = []
        equity_values: list[float] = []
        equity_index: list[pd.Timestamp] = []

        for timestamp, row in data.iloc[50:].iterrows():
            price = float(row["close"])
            current_equity = cash + position_qty * price
            equity_values.append(current_equity)
            equity_index.append(timestamp)

            if position_qty > 0:
                exit_reason = None
                if price <= stop_loss:
                    exit_reason = "stop_loss"
                elif price >= target:
                    exit_reason = "profit_target"
                elif detect_rsi_divergence(data.loc[:timestamp].tail(12)):
                    exit_reason = "rsi_divergence"
                elif row.get("relative_volume", 1) < 0.8 and row.get("ema_9", 0) < row.get("ema_20", 0):
                    exit_reason = "momentum_weakened"

                if exit_reason and open_trade is not None:
                    exit_price = self._apply_slippage(price, "sell")
                    proceeds = exit_price * position_qty - self.config.commission_per_share * position_qty
                    cash += proceeds
                    pnl = (exit_price - open_trade.entry_price) * position_qty
                    open_trade.exit_time = str(timestamp)
                    open_trade.exit_price = round(exit_price, 4)
                    open_trade.pnl = round(pnl, 2)
                    open_trade.reason = exit_reason
                    trades.append(open_trade)
                    position_qty = 0
                    open_trade = None
                continue

            buy_signal = (
                row.get("relative_volume", 0) > self.config.relative_volume_threshold
                and row["close"] > row.get("vwap", float("inf"))
                and row.get("ema_9", 0) > row.get("ema_20", 0)
                and 55 <= row.get("rsi", 0) <= 75
            )
            if not buy_signal:
                continue

            atr = float(row.get("atr", 0) or price * 0.02)
            risk_per_share = max(atr * self.config.stop_atr_multiple, price * 0.015)
            risk_budget = current_equity * self.config.risk_per_trade_pct
            qty = int(risk_budget // risk_per_share)
            if qty <= 0:
                continue
            fill_price = self._apply_slippage(price, "buy")
            cost = fill_price * qty + self.config.commission_per_share * qty
            if cost > cash:
                qty = int(cash // fill_price)
                cost = fill_price * qty
            if qty <= 0:
                continue

            cash -= cost
            position_qty = qty
            entry_price = fill_price
            stop_loss = entry_price - risk_per_share
            target = entry_price + risk_per_share * self.config.target_r_multiple
            open_trade = BacktestTrade(
                symbol=symbol,
                entry_time=str(timestamp),
                exit_time=None,
                entry_price=round(entry_price, 4),
                exit_price=None,
                quantity=qty,
            )

        if position_qty > 0 and open_trade is not None:
            final_price = float(data.iloc[-1]["close"])
            exit_price = self._apply_slippage(final_price, "sell")
            cash += exit_price * position_qty
            open_trade.exit_time = str(data.index[-1])
            open_trade.exit_price = round(exit_price, 4)
            open_trade.pnl = round((exit_price - open_trade.entry_price) * position_qty, 2)
            open_trade.reason = "end_of_backtest"
            trades.append(open_trade)

        equity_curve = pd.Series(equity_values, index=equity_index, name="equity")
        trade_pnls = [trade.pnl or 0.0 for trade in trades]
        report = build_report(self.config.initial_capital, equity_curve, trade_pnls)
        return BacktestResult(equity_curve=equity_curve, trades=trades, report=report)

    def _apply_slippage(self, price: float, side: str) -> float:
        multiplier = 1 + self.config.slippage_bps / 10_000 if side == "buy" else 1 - self.config.slippage_bps / 10_000
        return price * multiplier

