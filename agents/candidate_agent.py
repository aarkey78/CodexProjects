from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Any, Literal

from agents.base import AgentResult
from agents.momentum_agent import MomentumAgent
from agents.technical_agent import TechnicalAnalysisAgent
from agents.volume_agent import VolumeAgent
from config.settings import Settings
from data.alpha_vantage_client import AlphaVantageClient
from data.options_client import AlpacaOptionsClient, OptionsChainFilters


SetupType = Literal["DAY_TRADE_LONG", "SWING_LONG", "PUT_SIDE_PRESSURE", "WATCH_ONLY", "AVOID_CHOP"]


@dataclass(slots=True)
class CandidateScanConfig:
    expiration_days: int = 65
    monthly_only: bool = True
    min_score: float = 55.0
    limit: int = 10
    market_trend_bullish: bool = True


@dataclass(slots=True)
class CandidateResult:
    symbol: str
    final_score: float
    setup: SetupType
    direction: str
    trade_horizon: str
    options_bias: str
    monthly_expiration_pressure: str
    technical_confirmation: bool
    relative_volume: float
    rsi: float
    latest_price: float
    top_contract: str | None
    top_unusual_activity_score: float | None
    call_put_premium_ratio: float | None
    call_put_open_interest_ratio: float | None
    avg_volume_open_interest_ratio: float
    risk_notes: list[str]
    reasoning: str
    components: dict[str, float]
    top_contracts: list[dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class OptionsMomentumCandidateAgent:
    """Builds a ranked shortlist from options pressure plus technical momentum."""

    name = "options_momentum_candidates"

    def __init__(
        self,
        settings: Settings,
        market_data: AlphaVantageClient,
        options_client: AlpacaOptionsClient,
    ) -> None:
        self.settings = settings
        self.market_data = market_data
        self.options_client = options_client
        self.momentum = MomentumAgent()
        self.volume = VolumeAgent()
        self.technical = TechnicalAnalysisAgent()

    async def scan(
        self,
        symbols: list[str] | None = None,
        config: CandidateScanConfig | None = None,
    ) -> list[CandidateResult]:
        config = config or CandidateScanConfig()
        symbols = symbols or self.settings.watchlist_symbols
        results: list[CandidateResult] = []

        for symbol in symbols:
            try:
                candidate = await self.analyze_symbol(symbol.upper(), config)
            except Exception as exc:
                candidate = CandidateResult(
                    symbol=symbol.upper(),
                    final_score=0.0,
                    setup="AVOID_CHOP",
                    direction="none",
                    trade_horizon="none",
                    options_bias="unknown",
                    monthly_expiration_pressure="unknown",
                    technical_confirmation=False,
                    relative_volume=0.0,
                    rsi=0.0,
                    latest_price=0.0,
                    top_contract=None,
                    top_unusual_activity_score=None,
                    call_put_premium_ratio=None,
                    call_put_open_interest_ratio=None,
                    avg_volume_open_interest_ratio=0.0,
                    risk_notes=[f"Analysis failed: {exc}"],
                    reasoning="Skipped because one or more data sources failed.",
                    components={},
                    top_contracts=[],
                )
            if candidate.final_score >= config.min_score:
                results.append(candidate)

        results.sort(key=lambda item: item.final_score, reverse=True)
        return results[: config.limit]

    async def analyze_symbol(self, symbol: str, config: CandidateScanConfig) -> CandidateResult:
        intraday = await self.market_data.intraday(symbol, interval="5min")
        daily = await self.market_data.daily(symbol)
        momentum = await self.momentum.analyze(symbol, intraday)
        volume = await self.volume.analyze(symbol, daily)
        technical = await self.technical.analyze(symbol, intraday)
        options_payload = await self.options_client.get_chain(
            symbol,
            OptionsChainFilters(
                option_type="all",
                expiration_date_gte=date.today(),
                expiration_date_lte=date.today() + timedelta(days=config.expiration_days),
                monthly_only=config.monthly_only,
                include_open_interest=True,
                min_unusual_score=0.0,
                limit=750,
            ),
        )
        return score_options_momentum_candidate(
            symbol=symbol,
            momentum=momentum,
            volume=volume,
            technical=technical,
            options_payload=options_payload,
            market_trend_bullish=config.market_trend_bullish,
        )


def score_options_momentum_candidate(
    symbol: str,
    momentum: AgentResult,
    volume: AgentResult,
    technical: AgentResult,
    options_payload: dict[str, Any],
    market_trend_bullish: bool = True,
) -> CandidateResult:
    summary = options_payload.get("summary", {})
    contracts = options_payload.get("contracts", [])
    flow_bias = summary.get("flow_bias", "neutral")
    pressure_score = float(summary.get("monthly_expiration_pressure_score") or 0.0)
    top_activity_score = float(summary.get("top_unusual_activity_score") or 0.0)
    relative_volume = float(momentum.features.get("relative_volume") or 0.0)
    rsi = float(technical.features.get("rsi") or 0.0)
    latest_price = float(momentum.features.get("latest_price") or technical.features.get("close") or 0.0)
    above_vwap = bool(momentum.features.get("above_vwap") or latest_price > float(technical.features.get("vwap") or 10**9))
    ema_confirmed = float(technical.features.get("ema_9") or 0.0) > float(technical.features.get("ema_20") or 0.0)
    macd_positive = float(technical.features.get("macd") or 0.0) > float(technical.features.get("macd_signal") or 0.0)
    rsi_window = 52 <= rsi <= 78
    technical_confirmation = above_vwap and ema_confirmed and rsi_window

    avg_spread_quality = _average_spread_quality(contracts)
    liquidity_component = avg_spread_quality * 5
    options_component = min(top_activity_score, 100) * 0.35
    pressure_component = pressure_score * 0.20
    technical_component = technical.score * 20
    relative_volume_component = min(relative_volume / 3.0, 1.0) * 10
    market_component = 10.0 if market_trend_bullish else 2.0
    final_score = round(
        options_component
        + pressure_component
        + technical_component
        + relative_volume_component
        + market_component
        + liquidity_component,
        2,
    )

    direction = "long" if flow_bias == "call_heavy" else "bearish" if flow_bias == "put_heavy" else "watch"
    setup: SetupType = "AVOID_CHOP"
    trade_horizon = "none"
    if flow_bias == "put_heavy" and final_score >= 60:
        setup = "PUT_SIDE_PRESSURE"
        trade_horizon = "day/swing"
    elif final_score >= 75 and technical_confirmation and relative_volume >= 2:
        setup = "DAY_TRADE_LONG"
        trade_horizon = "intraday"
    elif final_score >= 70 and technical_confirmation and summary.get("monthly_expiration_pressure") in {"medium", "high"}:
        setup = "SWING_LONG"
        trade_horizon = "2-10 trading days"
    elif final_score >= 55:
        setup = "WATCH_ONLY"
        trade_horizon = "wait for confirmation"

    risk_notes = _risk_notes(summary, contracts, technical_confirmation, market_trend_bullish)
    reasoning = _build_reasoning(
        symbol=symbol,
        final_score=final_score,
        setup=setup,
        flow_bias=flow_bias,
        pressure=summary.get("monthly_expiration_pressure", "unknown"),
        top_contract=summary.get("top_contract"),
        technical_confirmation=technical_confirmation,
        relative_volume=relative_volume,
        rsi=rsi,
    )

    return CandidateResult(
        symbol=symbol,
        final_score=final_score,
        setup=setup,
        direction=direction,
        trade_horizon=trade_horizon,
        options_bias=flow_bias,
        monthly_expiration_pressure=summary.get("monthly_expiration_pressure", "unknown"),
        technical_confirmation=technical_confirmation,
        relative_volume=round(relative_volume, 3),
        rsi=round(rsi, 2),
        latest_price=round(latest_price, 2),
        top_contract=summary.get("top_contract"),
        top_unusual_activity_score=summary.get("top_unusual_activity_score"),
        call_put_premium_ratio=summary.get("call_put_premium_ratio"),
        call_put_open_interest_ratio=summary.get("call_put_open_interest_ratio"),
        avg_volume_open_interest_ratio=float(summary.get("avg_volume_open_interest_ratio") or 0.0),
        risk_notes=risk_notes,
        reasoning=reasoning,
        components={
            "options_activity": round(options_component, 2),
            "monthly_expiration_pressure": round(pressure_component, 2),
            "technical_momentum": round(technical_component, 2),
            "relative_volume": round(relative_volume_component, 2),
            "market_alignment": round(market_component, 2),
            "liquidity": round(liquidity_component, 2),
        },
        top_contracts=_top_contracts(contracts),
    )


def _average_spread_quality(contracts: list[dict[str, Any]]) -> float:
    if not contracts:
        return 0.0
    top = _top_contracts(contracts, limit=20)
    qualities = [1 - min(float(contract.get("spread_pct") or 1.0), 1.0) for contract in top]
    return sum(qualities) / len(qualities) if qualities else 0.0


def _top_contracts(contracts: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    fields = [
        "contract_symbol",
        "option_type",
        "expiration_date",
        "strike",
        "mid",
        "implied_volatility",
        "delta",
        "gamma",
        "open_interest",
        "volume_open_interest_ratio",
        "premium_proxy",
        "unusual_activity_score",
    ]
    sorted_contracts = sorted(contracts, key=lambda item: item.get("unusual_activity_score", 0), reverse=True)
    return [{field: contract.get(field) for field in fields} for contract in sorted_contracts[:limit]]


def _risk_notes(
    summary: dict[str, Any],
    contracts: list[dict[str, Any]],
    technical_confirmation: bool,
    market_trend_bullish: bool,
) -> list[str]:
    notes: list[str] = []
    if not technical_confirmation:
        notes.append("Technical confirmation is incomplete; wait for VWAP/EMA/RSI alignment.")
    if not market_trend_bullish:
        notes.append("Broad market trend is not bullish; reduce size or avoid long-only trades.")
    if float(summary.get("total_open_interest") or 0.0) < 1000:
        notes.append("Low total open interest can make signals noisy.")
    avg_spread = _average_spread_quality(contracts)
    if avg_spread < 0.75:
        notes.append("Top contracts have wider spreads; use limits and smaller size.")
    if float(summary.get("avg_iv") or 0.0) > 1.2:
        notes.append("Average IV is elevated; option premium may be expensive.")
    if not notes:
        notes.append("Paper-trade only until this setup has a validated sample.")
    return notes


def _build_reasoning(
    symbol: str,
    final_score: float,
    setup: SetupType,
    flow_bias: str,
    pressure: str,
    top_contract: str | None,
    technical_confirmation: bool,
    relative_volume: float,
    rsi: float,
) -> str:
    return (
        f"{symbol} scored {final_score:.1f} as {setup}. Options bias is {flow_bias}, "
        f"monthly expiration pressure is {pressure}, top contract is {top_contract}. "
        f"Technical confirmation={technical_confirmation}, relative volume={relative_volume:.2f}, RSI={rsi:.1f}."
    )

