from __future__ import annotations

from itertools import product

import pandas as pd

from backtesting.engine import BacktestConfig, BacktestEngine, BacktestResult


class WalkForwardOptimizer:
    """Grid-search walk-forward optimizer for core momentum parameters."""

    def __init__(self, base_config: BacktestConfig | None = None) -> None:
        self.base_config = base_config or BacktestConfig()

    def optimize(
        self,
        symbol: str,
        candles: pd.DataFrame,
        rel_volume_grid: list[float] | None = None,
        stop_atr_grid: list[float] | None = None,
    ) -> dict:
        rel_volume_grid = rel_volume_grid or [2.0, 2.5, 3.0, 3.5]
        stop_atr_grid = stop_atr_grid or [1.0, 1.5, 2.0]
        best_result: BacktestResult | None = None
        best_config: BacktestConfig | None = None

        for rel_vol, stop_atr in product(rel_volume_grid, stop_atr_grid):
            config = BacktestConfig(
                initial_capital=self.base_config.initial_capital,
                risk_per_trade_pct=self.base_config.risk_per_trade_pct,
                commission_per_share=self.base_config.commission_per_share,
                slippage_bps=self.base_config.slippage_bps,
                relative_volume_threshold=rel_vol,
                stop_atr_multiple=stop_atr,
                target_r_multiple=self.base_config.target_r_multiple,
            )
            result = BacktestEngine(config).run(symbol, candles)
            if best_result is None or (result.report and best_result.report and result.report.sharpe_ratio > best_result.report.sharpe_ratio):
                best_result = result
                best_config = config

        return {
            "best_config": best_config,
            "best_report": best_result.report.as_dict() if best_result and best_result.report else {},
        }

