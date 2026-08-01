import os
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

# picks ENV from system environment, defaults to "dev"
env = os.getenv("ENV", "dev")


class Settings(BaseSettings):
    ENV: str = "dev"

    DATABASE_URL: str = ""
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_TIMEOUT: int = 30

    FRONTEND_URL: str = ""

    # Create a property to use in your code
    @property
    def FRONTEND_URL_LIST(self) -> List[str]:
        urls = [item.strip() for item in self.FRONTEND_URL.split(",") if item.strip()]
        return urls if urls else [""]

    LOGGING_LEVEL: str = "INFO"

    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- ML pipeline (vendored) + orchestrator ---
    FINNHUB_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    SCHEDULER_ENABLED: bool = False
    SCHEDULER_INTERVAL_SECONDS: int = 3600
    SCHEDULER_LOOKBACK_HOURS: int = 24
    # Quant metrics cache TTL — fundamentals move slowly; caching cuts yfinance
    # calls and gives per-cycle ticker dedup for free. 0 disables the cache.
    QUANT_CACHE_TTL_SECONDS: int = 3600
    # Agent-suggested thesis edits (the proposals queue). Up to one extra LLM
    # call per thesis per sweep — firing theses included (fresh news can still
    # surface a new catalyst), but the scheduler's change-gate skips the call
    # when nothing moved since the last sweep. Off by default so an unattended
    # sweep can't spend tokens nobody asked for.
    PROPOSALS_ENABLED: bool = False

    TELEGRAM_BOT_TOKEN: str = ""
    TOKEN_TTL_SECONDS: int = 600
    TELEGRAM_BOT_URL: str = ""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / f".env.{env}",
        extra="ignore",
        case_sensitive=True
    )


settings = Settings()
