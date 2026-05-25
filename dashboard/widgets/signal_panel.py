from __future__ import annotations

import streamlit as st

from agents.base import TradeSignal


def render_signal(signal: TradeSignal) -> None:
    st.metric(label=f"{signal.symbol} {signal.action}", value=f"{signal.confidence:.2f}")
    st.write(signal.reasoning)
    st.json({"features": signal.features, "risk": signal.risk})

