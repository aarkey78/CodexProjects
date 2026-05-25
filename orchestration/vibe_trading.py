from __future__ import annotations

import logging
from dataclasses import asdict

import httpx

from agents.base import AgentResult, TradeSignal
from agents.journal_agent import JournalAgent
from agents.momentum_agent import MomentumAgent
from agents.options_flow_agent import OptionsFlowAgent
from agents.risk_agent import RiskAgent
from agents.sentiment_agent import SentimentAgent
from agents.technical_agent import TechnicalAnalysisAgent
from agents.volume_agent import VolumeAgent
from config.settings import Settings
from data.alpha_vantage_client import AlphaVantageClient
from data.options_client import AlpacaOptionsClient
from strategies.momentum_strategy import MomentumStrategy

logger = logging.getLogger(__name__)


class VibeTradingOrchestrator:
    """Local orchestration layer with optional Vibe-Trading endpoint delegation."""

    def __init__(self, settings: Settings, market_data: AlphaVantageClient) -> None:
        self.settings = settings
        self.market_data = market_data
        self.momentum = MomentumAgent()
        self.volume = VolumeAgent()
        self.technical = TechnicalAnalysisAgent()
        self.sentiment = SentimentAgent(settings, market_data)
        self.options_flow = OptionsFlowAgent(AlpacaOptionsClient(settings))
        self.risk = RiskAgent(settings)
        self.journal = JournalAgent()
        self.strategy = MomentumStrategy()

    async def scan(self, symbols: list[str] | None = None) -> list[AgentResult]:
        symbols = symbols or self.settings.watchlist_symbols
        candles_by_symbol = {
            symbol: await self.market_data.intraday(symbol, interval="5min")
            for symbol in symbols
        }
        return await self.momentum.rank(candles_by_symbol)

    async def generate_signal(self, symbol: str, market_trend_bullish: bool = True) -> TradeSignal:
        if self.settings.vibe_trading_endpoint:
            delegated = await self._delegate_to_vibe(symbol)
            if delegated is not None:
                return delegated

        intraday = await self.market_data.intraday(symbol, interval="5min")
        daily = await self.market_data.daily(symbol)
        momentum = await self.momentum.analyze(symbol, intraday)
        volume = await self.volume.analyze(symbol, daily)
        technical = await self.technical.analyze(symbol, intraday)
        sentiment = await self.sentiment.analyze(symbol)
        options_flow = await self.options_flow.analyze(symbol)

        signal = self.strategy.generate(
            symbol=symbol,
            momentum=momentum,
            volume=volume,
            technical=technical,
            sentiment=sentiment,
            market_trend_bullish=market_trend_bullish,
        )
        risk_result = await self.risk.analyze(signal)
        await self.journal.record_signal(
            signal=signal,
            agent_results=[momentum, volume, technical, sentiment, options_flow, risk_result],
        )
        return signal

    async def _delegate_to_vibe(self, symbol: str) -> TradeSignal | None:
        """Call a local Vibe-Trading service if the user exposes one."""

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.settings.vibe_trading_endpoint.rstrip('/')}/api/run",
                    json={
                        "task": (
                            f"Analyze {symbol} for momentum breakout, unusual volume, "
                            "risk sizing, and paper-trading readiness."
                        )
                    },
                )
                response.raise_for_status()
                payload = response.json()
            return TradeSignal(
                symbol=symbol,
                action=payload.get("action", "HOLD"),
                confidence=float(payload.get("confidence", 0.5)),
                reasoning=payload.get("reasoning", "Delegated to Vibe-Trading."),
                features=payload,
            )
        except Exception as exc:
            logger.warning("Vibe-Trading delegation failed; using local agents: %s", exc)
            return None

    @staticmethod
    def serialize_signal(signal: TradeSignal) -> dict:
        payload = asdict(signal)
        payload["created_at"] = signal.created_at.isoformat()
        return payload
