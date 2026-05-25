from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from agents.base import AgentResult
from config.settings import Settings
from data.alpha_vantage_client import AlphaVantageClient

logger = logging.getLogger(__name__)


class SentimentAgent:
    """Uses OpenAI when configured and falls back to Alpha Vantage sentiment fields."""

    name = "sentiment"

    def __init__(self, settings: Settings, market_data: AlphaVantageClient) -> None:
        self.settings = settings
        self.market_data = market_data
        self.system_prompt = Path("config/prompts/sentiment_system.txt").read_text(encoding="utf-8")

    async def analyze(self, symbol: str, news_items: list[dict[str, Any]] | None = None) -> AgentResult:
        news = news_items if news_items is not None else await self.market_data.news_sentiment(symbol)
        if not news:
            return AgentResult(self.name, symbol, 0.5, False, "No news available.", {"sentiment": 0.5})

        if self.settings.openai_api_key:
            try:
                return await self._openai_summary(symbol, news)
            except Exception as exc:  # pragma: no cover - network/API dependent
                logger.warning("OpenAI sentiment failed, using numeric fallback: %s", exc)

        return self._numeric_fallback(symbol, news)

    async def _openai_summary(self, symbol: str, news: list[dict[str, Any]]) -> AgentResult:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        compact_news = [
            {
                "title": item.get("title"),
                "summary": item.get("summary"),
                "source": item.get("source"),
                "sentiment": item.get("overall_sentiment_score"),
            }
            for item in news[:8]
        ]
        response = await client.responses.create(
            model=self.settings.openai_model,
            input=[
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Analyze {symbol} news and return JSON with keys "
                        "sentiment_score, confidence, summary, catalysts, risks.\n"
                        f"News: {json.dumps(compact_news)}"
                    ),
                },
            ],
        )
        text = response.output_text.strip()
        payload = json.loads(text[text.find("{") : text.rfind("}") + 1])
        score = float(payload.get("sentiment_score", 0.5))
        confidence = float(payload.get("confidence", 0.5))
        return AgentResult(
            agent=self.name,
            symbol=symbol,
            score=score * confidence,
            passed=score > 0.7 and confidence > 0.4,
            reasoning=str(payload.get("summary", "AI sentiment analysis generated.")),
            features=payload,
        )

    def _numeric_fallback(self, symbol: str, news: list[dict[str, Any]]) -> AgentResult:
        scores: list[float] = []
        titles: list[str] = []
        for item in news[:10]:
            titles.append(str(item.get("title", "")))
            if item.get("ticker_sentiment"):
                for ticker in item["ticker_sentiment"]:
                    if ticker.get("ticker", "").upper() == symbol.upper():
                        scores.append(float(ticker.get("ticker_sentiment_score", 0)))
            elif item.get("overall_sentiment_score") is not None:
                scores.append(float(item.get("overall_sentiment_score", 0)))

        raw = sum(scores) / len(scores) if scores else 0.0
        normalized = max(0.0, min(1.0, 0.5 + raw))
        return AgentResult(
            agent=self.name,
            symbol=symbol,
            score=normalized,
            passed=normalized > 0.7,
            reasoning=f"News sentiment fallback score {normalized:.2f}. Latest catalysts: {', '.join(titles[:3])}",
            features={"sentiment_score": normalized, "news_count": len(news), "titles": titles[:5]},
        )

