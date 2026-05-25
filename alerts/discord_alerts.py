from __future__ import annotations

import logging

import httpx

from agents.base import TradeSignal
from config.settings import Settings

logger = logging.getLogger(__name__)


class DiscordAlerts:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def send_signal(self, signal: TradeSignal) -> bool:
        if not self.settings.discord_webhook_url:
            logger.info("Discord alert skipped; webhook not configured.")
            return False
        payload = {
            "content": (
                f"**{signal.action} {signal.symbol}** confidence={signal.confidence:.2f}\n"
                f"{signal.reasoning}"
            )
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(self.settings.discord_webhook_url, json=payload)
            response.raise_for_status()
        return True

