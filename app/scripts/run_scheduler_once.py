"""Run the orchestrator EXACTLY ONCE against the real DB, then exit.

This is the single-run harness: instead of enabling the timer loop
(SCHEDULER_ENABLED), it calls `scheduler.run_once()` one time so you can watch a
full cycle — news → classify → apply → quant → evaluate → persist — and inspect
what landed in the database.

Usage (host, with Postgres running via docker compose):

  # keyless (quant-only thesis):
  DATABASE_URL=postgresql+asyncpg://admin:admin123@localhost:5432/appdb \
  ENV=dev python -m app.scripts.run_scheduler_once

  # full (thesis has a catalyst): also export FINNHUB_API_KEY and OPENAI_API_KEY
"""
import asyncio
import warnings

# yfinance internals emit noisy pandas deprecation warnings — not our code, harmless.
warnings.filterwarnings("ignore", category=DeprecationWarning)
try:
    from pandas.errors import Pandas4Warning
    warnings.filterwarnings("ignore", category=Pandas4Warning)
except Exception:
    pass

from app.config import settings
from app.core.logger import logger  # noqa: F401 — import configures root logging
from app.database_registry import init_database_engine
from app.service.scheduler_service import scheduler


async def main() -> None:
    init_database_engine(settings.DATABASE_URL)
    await scheduler.run_once()
    print("✅ one cycle complete — check tbl_evaluations / tbl_catalysts for what landed")


if __name__ == "__main__":
    asyncio.run(main())
