"""Seed ONE demo thesis so the orchestrator has something to evaluate.

Two modes, so you can start keyless and then go full:

  * default (KEYLESS): a quant-only thesis — one quant condition, no catalysts.
    The scheduler skips news/LLM entirely and evaluates on yfinance alone, so
    you need NO API keys for your first real run.

  * --with-catalyst: also adds a catalyst. A real run then classifies live news,
    so it needs FINNHUB_API_KEY + OPENAI_API_KEY in the environment.

Idempotent on the user + stock (get-or-create), so re-running just adds another
thesis rather than crashing on unique constraints.

Usage (host, with Postgres running via docker compose):

  DATABASE_URL=postgresql+asyncpg://admin:admin123@localhost:5432/appdb \
  ENV=dev python -m app.scripts.seed_demo_thesis --ticker NVDA
"""
import argparse
import asyncio
from decimal import Decimal

from sqlalchemy import select, text

from app.config import settings
from app.database_registry import get_sessionmaker, init_database_engine
from common.enums.ThesesEnum import CatalystModeEnum, QuantModeEnum
from app.models import Catalyst, QuantCondition, Stock, Theses, User


async def _get_or_create_user(session, email: str) -> User:
    user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None:
        user = User(email=email, username="demo", password_hash="!seed-not-a-login!")
        session.add(user)
        await session.flush()
    return user


async def _get_or_create_stock(session, ticker: str) -> Stock:
    stock = (await session.execute(select(Stock).where(Stock.ticker == ticker))).scalar_one_or_none()
    if stock is None:
        stock = Stock(ticker=ticker)
        session.add(stock)
        await session.flush()
    return stock


async def _reset_demo_db(session) -> int:
    """Wipe ALL data in the demo DB (every appdb.tbl_* table) so repeated
    experiments start clean. TRUNCATE ... CASCADE handles the audit-history
    foreign keys that block ordinary row deletes. Safe here because this is a
    throwaway demo database — do NOT point this at a database with real data.
    Returns the number of tables truncated."""
    tables = (await session.execute(
        text("SELECT tablename FROM pg_tables WHERE schemaname = 'appdb'")
    )).scalars().all()
    if tables:
        joined = ", ".join(f'appdb."{t}"' for t in tables)
        await session.execute(text(f"TRUNCATE {joined} RESTART IDENTITY CASCADE"))
    return len(tables)


async def main(ticker: str, with_catalyst: bool, metric: str, operator: str, value: str, clean: bool,
               catalyst_desc: str | None = None) -> None:
    init_database_engine(settings.DATABASE_URL)
    session_maker = get_sessionmaker()
    async with session_maker() as session:
        if clean:
            n = await _reset_demo_db(session)
            print(f"🧹 reset demo DB — truncated {n} tables")

        user = await _get_or_create_user(session, "demo@kestrel.local")
        stock = await _get_or_create_stock(session, ticker)

        thesis = Theses(
            user_id=user.user_id,
            stock_id=stock.stock_id,
            quant_mode=QuantModeEnum.ANY,
            catalyst_mode=CatalystModeEnum.ANY,  # with 0 catalysts this never blocks the signal
            notes="seed demo thesis",
        )
        session.add(thesis)
        await session.flush()

        # Loosen the threshold (e.g. --value 1000) to watch a signal FIRE; tighten
        # it (e.g. --value 5) to watch the same thesis go 'not_met' with a reason.
        session.add(QuantCondition(
            theses_id=thesis.theses_id, metric=metric, operator=operator, value=Decimal(value),
        ))

        if with_catalyst:
            description = catalyst_desc or f"{ticker} beats quarterly earnings estimates"
            session.add(Catalyst(
                theses_id=thesis.theses_id,
                state="unconfirmed",  # ML CatalystState values are lowercase
                description=description,
                evidence=[],
            ))

        await session.commit()

        print("✅ seeded")
        print(f"   user_id   : {user.user_id}  (demo@kestrel.local)")
        print(f"   thesis_id : {thesis.theses_id}")
        print(f"   ticker    : {ticker}")
        print(f"   condition : {metric} {operator} {value}")
        print(f"   catalyst  : {'yes — real run needs FINNHUB + OPENAI keys' if with_catalyst else 'none — KEYLESS run (yfinance only)'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed one demo thesis for the orchestrator.")
    parser.add_argument("--ticker", default="NVDA", help="stock ticker (default NVDA)")
    parser.add_argument("--metric", default="forward_pe", help="quant metric (see quant_service.METRIC_MAP)")
    parser.add_argument("--operator", default="<", help="comparison operator: < <= > >= == !=")
    parser.add_argument("--value", default="1000", help="threshold; loose (1000) fires, tight (5) → not_met")
    parser.add_argument("--with-catalyst", action="store_true",
                        help="also add a catalyst (real run then needs API keys)")
    parser.add_argument("--catalyst-desc", default=None,
                        help="catalyst description to classify news against (implies --with-catalyst)")
    parser.add_argument("--clean", action="store_true",
                        help="delete existing demo theses first (avoid pile-up)")
    args = parser.parse_args()
    with_catalyst = args.with_catalyst or args.catalyst_desc is not None
    asyncio.run(main(args.ticker, with_catalyst, args.metric, args.operator, args.value, args.clean,
                     args.catalyst_desc))
