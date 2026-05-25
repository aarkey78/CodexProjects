from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "Vibe Momentum Trading Platform"
    environment: Literal["local", "paper", "live"] = "paper"
    log_level: str = "INFO"

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@postgres:5432/trading"
    )
    redis_url: str = "redis://redis:6379/0"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"

    alpha_vantage_api_key: str | None = None
    alpha_vantage_base_url: str = "https://www.alphavantage.co/query"
    alpha_vantage_calls_per_minute: int = 5

    alpaca_api_key: str | None = None
    alpaca_secret_key: str | None = None
    alpaca_paper: bool = True

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    discord_webhook_url: str | None = None
    notion_api_key: str | None = None
    notion_database_id: str | None = None

    watchlist: str = "AAPL,MSFT,NVDA,TSLA,AMD,META,AMZN,SPY,QQQ"
    max_daily_risk_pct: float = 0.02
    max_position_risk_pct: float = 0.005
    default_account_equity: float = 100_000.0

    enable_live_trading: bool = False
    enable_mock_data: bool = True
    vibe_trading_endpoint: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def watchlist_symbols(self) -> list[str]:
        return [symbol.strip().upper() for symbol in self.watchlist.split(",") if symbol.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

