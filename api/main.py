from __future__ import annotations

from dataclasses import asdict
from datetime import date, timedelta
from typing import Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from alerts.discord_alerts import DiscordAlerts
from alerts.telegram_alerts import TelegramAlerts
from agents.execution_agent import ExecutionAgent
from agents.options_flow_agent import OptionsFlowAgent
from backtesting.engine import BacktestConfig, BacktestEngine
from config.logging import configure_logging
from config.settings import get_settings
from data.alpha_vantage_client import AlphaVantageClient
from data.alpaca_client import AlpacaTradingClient, BrokerOrder
from data.market_cache import MarketCache
from data.options_client import AlpacaOptionsClient, OptionsChainFilters
from orchestration.vibe_trading import VibeTradingOrchestrator

settings = get_settings()
configure_logging(settings.log_level)
cache = MarketCache(settings.redis_url)
market_data = AlphaVantageClient(settings, cache)
broker = AlpacaTradingClient(settings)
options_client = AlpacaOptionsClient(settings)
options_agent = OptionsFlowAgent(options_client)
orchestrator = VibeTradingOrchestrator(settings, market_data)
execution_agent = ExecutionAgent(broker)
telegram_alerts = TelegramAlerts(settings)
discord_alerts = DiscordAlerts(settings)

app = FastAPI(title=settings.app_name, version="0.1.0")


class OrderRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=16)
    qty: float = Field(..., gt=0)
    side: Literal["buy", "sell"]
    order_type: Literal["market", "limit", "stop"] = "market"
    limit_price: float | None = None
    stop_price: float | None = None
    time_in_force: str = "day"


class BacktestRequest(BaseModel):
    symbol: str
    initial_capital: float = 100_000
    risk_per_trade_pct: float = 0.005
    relative_volume_threshold: float = 3.0


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "environment": settings.environment,
        "paper_trading": settings.alpaca_paper,
        "mock_data": settings.enable_mock_data,
    }


@app.get("/scan")
async def scan(symbols: str | None = Query(default=None, description="Comma-separated symbols")) -> list[dict]:
    selected = [item.strip().upper() for item in symbols.split(",")] if symbols else None
    results = await orchestrator.scan(selected)
    return [asdict(result) for result in results]


@app.get("/signals/{symbol}")
async def signal(symbol: str, background_tasks: BackgroundTasks, execute: bool = False) -> dict:
    trade_signal = await orchestrator.generate_signal(symbol.upper())
    execution_result = None
    if execute and trade_signal.action in {"BUY", "SELL"}:
        execution_result = await execution_agent.analyze(trade_signal, execute=True)
    if trade_signal.action in {"BUY", "SELL"}:
        background_tasks.add_task(telegram_alerts.send_signal, trade_signal)
        background_tasks.add_task(discord_alerts.send_signal, trade_signal)
    payload = orchestrator.serialize_signal(trade_signal)
    if execution_result:
        payload["execution"] = asdict(execution_result)
    return payload


@app.get("/account")
async def account() -> dict:
    return await broker.account()


@app.get("/positions")
async def positions() -> list[dict]:
    return await broker.positions()


@app.get("/options/{symbol}")
async def options_chain(
    symbol: str,
    option_type: Literal["all", "call", "put"] = "all",
    expiration_days: int = Query(default=45, ge=1, le=730),
    expiration_date_gte: date | None = None,
    expiration_date_lte: date | None = None,
    strike_min: float | None = Query(default=None, gt=0),
    strike_max: float | None = Query(default=None, gt=0),
    min_iv: float | None = Query(default=None, ge=0),
    max_iv: float | None = Query(default=None, ge=0),
    min_delta: float | None = Query(default=None, ge=-1, le=1),
    max_delta: float | None = Query(default=None, ge=-1, le=1),
    min_gamma: float | None = Query(default=None, ge=0),
    max_gamma: float | None = Query(default=None, ge=0),
    min_unusual_score: float = Query(default=0.0, ge=0, le=100),
    limit: int = Query(default=250, ge=1, le=2000),
) -> dict:
    filters = OptionsChainFilters(
        option_type=option_type,
        expiration_date_gte=expiration_date_gte or date.today(),
        expiration_date_lte=expiration_date_lte or (date.today() + timedelta(days=expiration_days)),
        strike_min=strike_min,
        strike_max=strike_max,
        min_iv=min_iv,
        max_iv=max_iv,
        min_delta=min_delta,
        max_delta=max_delta,
        min_gamma=min_gamma,
        max_gamma=max_gamma,
        min_unusual_score=min_unusual_score,
        limit=limit,
    )
    payload = await options_client.get_chain(symbol.upper(), filters)
    flow_result = await options_agent.analyze(symbol.upper(), payload["contracts"], filters)
    payload["analysis"] = asdict(flow_result)
    return payload


@app.post("/orders")
async def submit_order(order_request: OrderRequest) -> dict:
    if not settings.alpaca_paper and not settings.enable_live_trading:
        raise HTTPException(status_code=403, detail="Live trading is disabled by configuration.")
    order = BrokerOrder(**order_request.model_dump())
    return await broker.submit_order(order)


@app.post("/backtest")
async def backtest(request: BacktestRequest) -> dict:
    candles = await market_data.daily(request.symbol, outputsize="full")
    config = BacktestConfig(
        initial_capital=request.initial_capital,
        risk_per_trade_pct=request.risk_per_trade_pct,
        relative_volume_threshold=request.relative_volume_threshold,
    )
    result = BacktestEngine(config).run(request.symbol.upper(), candles)
    return {
        "report": result.report.as_dict() if result.report else {},
        "trades": [asdict(trade) for trade in result.trades],
        "equity_curve": result.equity_curve.tail(500).to_dict(),
    }
