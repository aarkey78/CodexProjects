from __future__ import annotations

import logging

import httpx

from agents.base import TradeSignal
from config.settings import Settings

logger = logging.getLogger(__name__)


class TelegramAlerts:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def send_signal(self, signal: TradeSignal) -> bool:
        if not self.settings.telegram_bot_token or not self.settings.telegram_chat_id:
            logger.info("Telegram alert skipped; token/chat id not configured.")
            return False
        message = (
            f"{signal.action} {signal.symbol} | confidence={signal.confidence:.2f}\n"
            f"{signal.reasoning}\nRisk: {signal.risk}"
        )
        url = f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendMessage"
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json={"chat_id": self.settings.telegram_chat_id, "text": message})
            response.raise_for_status()
        return True

