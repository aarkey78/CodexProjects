from __future__ import annotations


def export_momentum_pine_script(strategy_name: str = "AI Momentum Signal") -> str:
    """Export a TradingView Pine Script approximation of the core signal."""

    return f"""//@version=5
indicator("{strategy_name}", overlay=true)
ema9 = ta.ema(close, 9)
ema20 = ta.ema(close, 20)
vwapValue = ta.vwap(hlc3)
rsiValue = ta.rsi(close, 14)
relVol = volume / ta.sma(volume, 20)
buySignal = relVol > 3 and close > vwapValue and ema9 > ema20 and rsiValue >= 55 and rsiValue <= 75
plot(ema9, color=color.teal)
plot(ema20, color=color.orange)
plot(vwapValue, color=color.blue)
plotshape(buySignal, title="AI Momentum BUY", style=shape.triangleup, location=location.belowbar, color=color.green)
alertcondition(buySignal, title="AI Momentum BUY", message="Momentum BUY conditions met")
"""

