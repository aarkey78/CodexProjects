from __future__ import annotations

import asyncio
from dataclasses import asdict

import pandas as pd
import streamlit as st

from backtesting.engine import BacktestConfig, BacktestEngine
from config.settings import get_settings
from data.alpha_vantage_client import AlphaVantageClient
from data.indicators import add_indicators
from data.market_cache import MarketCache
from orchestration.vibe_trading import VibeTradingOrchestrator


def run_async(coro):
    return asyncio.run(coro)


@st.cache_resource
def resources():
    settings = get_settings()
    cache = MarketCache(settings.redis_url)
    market_data = AlphaVantageClient(settings, cache)
    orchestrator = VibeTradingOrchestrator(settings, market_data)
    return settings, market_data, orchestrator


settings, market_data, orchestrator = resources()

st.set_page_config(page_title="AI Momentum Trading", layout="wide")
st.title("AI Momentum Trading Desk")

watchlist = st.sidebar.multiselect(
    "Watchlist",
    settings.watchlist_symbols,
    default=settings.watchlist_symbols[:5],
)
symbol = st.sidebar.selectbox("Symbol", watchlist or settings.watchlist_symbols)
run_scan = st.sidebar.button("Run Scan", type="primary")
run_signal = st.sidebar.button("Generate Signal")
run_backtest = st.sidebar.button("Run Backtest")

if run_scan:
    scan_results = run_async(orchestrator.scan(watchlist))
    st.subheader("Momentum Watchlist")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "symbol": item.symbol,
                    "score": item.score,
                    "passed": item.passed,
                    "reasoning": item.reasoning,
                    **item.features,
                }
                for item in scan_results
            ]
        ),
        use_container_width=True,
    )

left, middle, right = st.columns([1.2, 1, 1])

with left:
    st.subheader(f"{symbol} Chart")
    candles = run_async(market_data.intraday(symbol))
    enriched = add_indicators(candles)
    chart_cols = [col for col in ["close", "vwap", "ema_9", "ema_20"] if col in enriched]
    st.line_chart(enriched[chart_cols].tail(120), use_container_width=True)

with middle:
    st.subheader("Live Signal")
    if run_signal:
        trade_signal = run_async(orchestrator.generate_signal(symbol))
        st.metric(trade_signal.action, f"{trade_signal.confidence:.2f}")
        st.write(trade_signal.reasoning)
        st.json({"risk": trade_signal.risk, "features": trade_signal.features})
    else:
        st.caption("Generate a signal to populate this panel.")

with right:
    st.subheader("Backtest")
    if run_backtest:
        daily = run_async(market_data.daily(symbol, outputsize="full"))
        result = BacktestEngine(BacktestConfig()).run(symbol, daily)
        st.json(result.report.as_dict() if result.report else {})
        st.line_chart(result.equity_curve, use_container_width=True)
        st.dataframe(pd.DataFrame([asdict(trade) for trade in result.trades]), use_container_width=True)
    else:
        st.caption("Run a backtest to view performance.")

