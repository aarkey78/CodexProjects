from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass
from typing import Any, Literal

from config.settings import Settings

logger = logging.getLogger(__name__)


OrderSide = Literal["buy", "sell"]
OrderType = Literal["market", "limit", "stop"]


@dataclass
class BrokerOrder:
    symbol: str
    qty: float
    side: OrderSide
    order_type: OrderType = "market"
    time_in_force: str = "day"
    limit_price: float | None = None
    stop_price: float | None = None


class AlpacaTradingClient:
    """Async wrapper around alpaca-py with a safe mock mode."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = None
        if settings.alpaca_api_key and settings.alpaca_secret_key:
            try:
                from alpaca.trading.client import TradingClient

                self._client = TradingClient(
                    settings.alpaca_api_key,
                    settings.alpaca_secret_key,
                    paper=settings.alpaca_paper,
                )
            except Exception as exc:  # pragma: no cover - depends on SDK environment
                logger.warning("Alpaca client initialization failed, using mock mode: %s", exc)

    @property
    def is_live_enabled(self) -> bool:
        return bool(self._client and (self.settings.alpaca_paper or self.settings.enable_live_trading))

    async def account(self) -> dict[str, Any]:
        if not self._client:
            return {
                "status": "MOCK",
                "equity": str(self.settings.default_account_equity),
                "buying_power": str(self.settings.default_account_equity * 2),
                "paper": True,
            }
        account = await asyncio.to_thread(self._client.get_account)
        return _model_to_dict(account)

    async def positions(self) -> list[dict[str, Any]]:
        if not self._client:
            return []
        positions = await asyncio.to_thread(self._client.get_all_positions)
        return [_model_to_dict(position) for position in positions]

    async def submit_order(self, order: BrokerOrder) -> dict[str, Any]:
        if not self.is_live_enabled:
            logger.info("Mock order accepted: %s", order)
            return {"id": "mock-order", "status": "accepted", "mock": True, **asdict(order)}

        from alpaca.trading.enums import OrderSide as AlpacaOrderSide
        from alpaca.trading.enums import TimeInForce
        from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest, StopOrderRequest

        side = AlpacaOrderSide.BUY if order.side == "buy" else AlpacaOrderSide.SELL
        tif = TimeInForce.DAY if order.time_in_force.lower() == "day" else TimeInForce.GTC

        if order.order_type == "limit":
            request = LimitOrderRequest(
                symbol=order.symbol,
                qty=order.qty,
                side=side,
                time_in_force=tif,
                limit_price=order.limit_price,
            )
        elif order.order_type == "stop":
            request = StopOrderRequest(
                symbol=order.symbol,
                qty=order.qty,
                side=side,
                time_in_force=tif,
                stop_price=order.stop_price,
            )
        else:
            request = MarketOrderRequest(
                symbol=order.symbol,
                qty=order.qty,
                side=side,
                time_in_force=tif,
            )
        submitted = await asyncio.to_thread(self._client.submit_order, request)
        return _model_to_dict(submitted)

    async def cancel_all_orders(self) -> list[dict[str, Any]]:
        if not self._client:
            return []
        statuses = await asyncio.to_thread(self._client.cancel_orders)
        return [_model_to_dict(status) for status in statuses]


def _model_to_dict(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    if hasattr(model, "dict"):
        return model.dict()
    if hasattr(model, "__dict__"):
        return dict(model.__dict__)
    return {"value": str(model)}

