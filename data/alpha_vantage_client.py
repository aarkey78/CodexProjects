from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pandas as pd

from config.settings import Settings
from data.indicators import normalize_ohlcv
from data.market_cache import MarketCache

logger = logging.getLogger(__name__)


class AsyncRateLimiter:
    """Simple minute-window rate limiter for Alpha Vantage free-tier safety."""

    def __init__(self, calls_per_minute: int) -> None:
        self.calls_per_minute = max(calls_per_minute, 1)
        self._window_started = 0.0
        self._calls = 0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self._lock:
            loop_time = asyncio.get_running_loop().time()
            if loop_time - self._window_started >= 60:
                self._window_started = loop_time
                self._calls = 0
            if self._calls >= self.calls_per_minute:
                await asyncio.sleep(60 - (loop_time - self._window_started))
                self._window_started = asyncio.get_running_loop().time()
                self._calls = 0
            self._calls += 1


class AlphaVantageClient:
    """Async Alpha Vantage client with retry, rate limiting, cache, and mock fallback."""

    def __init__(self, settings: Settings, cache: MarketCache | None = None) -> None:
        self.settings = settings
        self.cache = cache or MarketCache(settings.redis_url)
        self.rate_limiter = AsyncRateLimiter(settings.alpha_vantage_calls_per_minute)

    async def _get(self, params: dict[str, Any], ttl_seconds: int = 300) -> dict[str, Any]:
        cache_key = f"alpha:{hash(frozenset(params.items()))}"
        cached = await self.cache.get_json(cache_key)
        if cached is not None:
            return cached

        if not self.settings.alpha_vantage_api_key:
            if self.settings.enable_mock_data:
                raise RuntimeError("Alpha Vantage key missing; mock fallback enabled.")
            raise RuntimeError("ALPHA_VANTAGE_API_KEY is required.")

        query = {**params, "apikey": self.settings.alpha_vantage_api_key}
        for attempt in range(3):
            try:
                await self.rate_limiter.wait()
                async with httpx.AsyncClient(timeout=20) as client:
                    response = await client.get(self.settings.alpha_vantage_base_url, params=query)
                    response.raise_for_status()
                    payload = response.json()
                if "Note" in payload or "Information" in payload:
                    raise RuntimeError(payload.get("Note") or payload.get("Information"))
                await self.cache.set_json(cache_key, payload, ttl_seconds)
                return payload
            except Exception as exc:
                if attempt == 2:
                    logger.warning("Alpha Vantage request failed: %s", exc)
                    raise
                await asyncio.sleep(2**attempt)
        raise RuntimeError("Unreachable Alpha Vantage retry path.")

    async def intraday(
        self,
        symbol: str,
        interval: str = "5min",
        outputsize: str = "compact",
    ) -> pd.DataFrame:
        params = {
            "function": "TIME_SERIES_INTRADAY",
            "symbol": symbol.upper(),
            "interval": interval,
            "outputsize": outputsize,
        }
        try:
            payload = await self._get(params, ttl_seconds=120)
            series_key = next(key for key in payload if key.startswith("Time Series"))
            return normalize_ohlcv(pd.DataFrame.from_dict(payload[series_key], orient="index"))
        except Exception:
            if self.settings.enable_mock_data:
                return self.mock_intraday(symbol)
            raise

    async def daily(self, symbol: str, outputsize: str = "compact") -> pd.DataFrame:
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol.upper(),
            "outputsize": outputsize,
        }
        try:
            payload = await self._get(params, ttl_seconds=3600)
            series_key = "Time Series (Daily)"
            return normalize_ohlcv(pd.DataFrame.from_dict(payload[series_key], orient="index"))
        except Exception:
            if self.settings.enable_mock_data:
                return self.mock_daily(symbol)
            raise

    async def news_sentiment(self, symbol: str, limit: int = 10) -> list[dict[str, Any]]:
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": symbol.upper(),
            "limit": limit,
            "sort": "LATEST",
        }
        try:
            payload = await self._get(params, ttl_seconds=900)
            return payload.get("feed", [])
        except Exception:
            if self.settings.enable_mock_data:
                return [
                    {
                        "title": f"{symbol.upper()} momentum watch",
                        "summary": "Mock catalyst: elevated volume and constructive sector tone.",
                        "overall_sentiment_score": 0.35,
                        "ticker_sentiment": [{"ticker": symbol.upper(), "ticker_sentiment_score": "0.45"}],
                    }
                ]
            raise

    async def sector_performance(self) -> dict[str, Any]:
        params = {"function": "SECTOR"}
        try:
            return await self._get(params, ttl_seconds=3600)
        except Exception:
            if self.settings.enable_mock_data:
                return {"Rank A: Real-Time Performance": {"Technology": "0.85%", "Financials": "-0.15%"}}
            raise

    async def technical_indicator(
        self,
        symbol: str,
        function: str,
        interval: str = "daily",
        time_period: int = 14,
        series_type: str = "close",
    ) -> dict[str, Any]:
        params = {
            "function": function.upper(),
            "symbol": symbol.upper(),
            "interval": interval,
            "time_period": time_period,
            "series_type": series_type,
        }
        return await self._get(params, ttl_seconds=900)

    @staticmethod
    def mock_intraday(symbol: str, periods: int = 120) -> pd.DataFrame:
        now = datetime.now(tz=UTC).replace(second=0, microsecond=0)
        index = pd.date_range(end=now, periods=periods, freq="5min")
        seed = sum(ord(char) for char in symbol)
        base = 50 + seed % 250
        drift = pd.Series(range(periods), index=index) * 0.035
        wave = pd.Series([(idx % 9 - 4) * 0.08 for idx in range(periods)], index=index)
        close = base + drift + wave
        volume = pd.Series([120_000 + (idx % 13) * 18_000 for idx in range(periods)], index=index)
        volume.iloc[-6:] = volume.iloc[-6:] * 3
        return normalize_ohlcv(
            pd.DataFrame(
                {
                    "open": close.shift(1).fillna(close.iloc[0] - 0.2),
                    "high": close + 0.35,
                    "low": close - 0.35,
                    "close": close,
                    "volume": volume,
                }
            )
        )

    @staticmethod
    def mock_daily(symbol: str, periods: int = 260) -> pd.DataFrame:
        end = datetime.now(tz=UTC).date()
        index = pd.date_range(end=end, periods=periods, freq="B")
        seed = sum(ord(char) for char in symbol)
        base = 40 + seed % 180
        trend = pd.Series(range(periods), index=index) * 0.08
        close = base + trend
        volume = pd.Series([2_000_000 + (idx % 20) * 80_000 for idx in range(periods)], index=index)
        return normalize_ohlcv(
            pd.DataFrame(
                {
                    "open": close.shift(1).fillna(close.iloc[0]),
                    "high": close + 1.1,
                    "low": close - 1.1,
                    "close": close,
                    "volume": volume,
                }
            )
        )

