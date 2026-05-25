from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    value: Any
    expires_at: float


class MarketCache:
    """Async cache with Redis support and an in-memory fallback."""

    def __init__(self, redis_url: str | None = None, default_ttl_seconds: int = 300) -> None:
        self.default_ttl_seconds = default_ttl_seconds
        self._memory: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
        self._redis = None
        if redis_url:
            try:
                from redis.asyncio import from_url

                self._redis = from_url(redis_url, decode_responses=True)
            except Exception as exc:  # pragma: no cover - optional dependency path
                logger.warning("Redis unavailable, using memory cache: %s", exc)

    async def get_json(self, key: str) -> Any | None:
        if self._redis is not None:
            cached = await self._redis.get(key)
            if cached is not None:
                return json.loads(cached)

        async with self._lock:
            entry = self._memory.get(key)
            if entry and entry.expires_at > time.time():
                return entry.value
            self._memory.pop(key, None)
        return None

    async def set_json(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        ttl = ttl_seconds or self.default_ttl_seconds
        if self._redis is not None:
            await self._redis.set(key, json.dumps(value, default=str), ex=ttl)
            return
        async with self._lock:
            self._memory[key] = CacheEntry(value=value, expires_at=time.time() + ttl)

    async def get_dataframe(self, key: str) -> pd.DataFrame | None:
        payload = await self.get_json(key)
        if payload is None:
            return None
        df = pd.DataFrame(payload["data"])
        if payload.get("index"):
            df.index = pd.to_datetime(payload["index"], utc=True)
        return df

    async def set_dataframe(self, key: str, df: pd.DataFrame, ttl_seconds: int | None = None) -> None:
        payload = {
            "index": [idx.isoformat() if hasattr(idx, "isoformat") else str(idx) for idx in df.index],
            "data": df.reset_index(drop=True).to_dict(orient="records"),
        }
        await self.set_json(key, payload, ttl_seconds)

