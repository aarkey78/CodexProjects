from __future__ import annotations

import asyncio
from dataclasses import asdict
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from backtesting.engine import BacktestConfig, BacktestEngine
from config.settings import get_settings
from data.alpha_vantage_client import AlphaVantageClient
from data.indicators import add_indicators
from data.market_cache import MarketCache
from data.options_client import AlpacaOptionsClient, OptionsChainFilters
from orchestration.vibe_trading import VibeTradingOrchestrator


def run_async(coro):
    return asyncio.run(coro)


@st.cache_resource
def resources():
    settings = get_settings()
    cache = MarketCache(settings.redis_url)
    market_data = AlphaVantageClient(settings, cache)
    options_client = AlpacaOptionsClient(settings)
    orchestrator = VibeTradingOrchestrator(settings, market_data)
    return settings, market_data, options_client, orchestrator


settings, market_data, options_client, orchestrator = resources()

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

st.sidebar.divider()
st.sidebar.subheader("Options")
option_type = st.sidebar.selectbox("Type", ["all", "call", "put"], index=0)
expiration_days = st.sidebar.slider("Expiration Days", min_value=1, max_value=180, value=45)
min_unusual_score = st.sidebar.slider("Min Activity Score", min_value=0, max_value=100, value=50)
iv_range = st.sidebar.slider("IV Range", min_value=0.0, max_value=3.0, value=(0.0, 3.0), step=0.05)
delta_range = st.sidebar.slider("Delta Range", min_value=-1.0, max_value=1.0, value=(-1.0, 1.0), step=0.05)
gamma_range = st.sidebar.slider("Gamma Range", min_value=0.0, max_value=1.0, value=(0.0, 1.0), step=0.01)
strike_min_input = st.sidebar.number_input("Min Strike", min_value=0.0, value=0.0, step=1.0)
strike_max_input = st.sidebar.number_input("Max Strike", min_value=0.0, value=0.0, step=1.0)
load_options = st.sidebar.button("Load Options")

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

st.divider()
st.subheader(f"{symbol} Options Chain")

if load_options:
    option_filters = OptionsChainFilters(
        option_type=option_type,
        expiration_date_gte=date.today(),
        expiration_date_lte=date.today() + timedelta(days=expiration_days),
        strike_min=strike_min_input or None,
        strike_max=strike_max_input or None,
        min_iv=iv_range[0],
        max_iv=iv_range[1],
        min_delta=delta_range[0],
        max_delta=delta_range[1],
        min_gamma=gamma_range[0],
        max_gamma=gamma_range[1],
        min_unusual_score=float(min_unusual_score),
        limit=500,
    )
    try:
        options_payload = run_async(options_client.get_chain(symbol, option_filters))
        summary = options_payload["summary"]
        metric_cols = st.columns(5)
        metric_cols[0].metric("Contracts", options_payload["contract_count"])
        metric_cols[1].metric("Flow Bias", summary["flow_bias"])
        metric_cols[2].metric("Call/Put Premium", summary["call_put_premium_ratio"])
        metric_cols[3].metric("Top Score", summary["top_unusual_activity_score"])
        metric_cols[4].metric("Avg IV", summary["avg_iv"])

        options_df = pd.DataFrame(options_payload["contracts"])
        if options_df.empty:
            st.warning("No contracts matched the selected filters.")
        else:
            display_columns = [
                "contract_symbol",
                "option_type",
                "expiration_date",
                "days_to_expiration",
                "strike",
                "bid",
                "ask",
                "mid",
                "implied_volatility",
                "delta",
                "gamma",
                "theta",
                "vega",
                "activity_proxy",
                "premium_proxy",
                "unusual_activity_score",
                "liquidity_bias",
            ]
            st.dataframe(
                options_df[[column for column in display_columns if column in options_df.columns]],
                use_container_width=True,
                hide_index=True,
            )
    except Exception as exc:
        st.error(f"Options data failed: {exc}")
else:
    st.caption("Use Load Options to fetch option-chain activity for the selected symbol.")
