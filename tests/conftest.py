"""
Shared pytest configuration.

asyncio_mode = auto (set in pytest.ini) means every async test function
is awaited automatically — no @pytest.mark.asyncio needed.

Teardown: clear all FastAPI dependency overrides after each test so
overrides don't leak between test classes or modules.
"""

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from app.database_registry import override_engine
from app.main import app

override_engine(create_async_engine("sqlite+aiosqlite:///:memory:"))


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """
    Guarantee a clean dependency override state for every test.
    Runs *after* each test (yield separates setup from teardown).
    Without this, an override set in one test leaks into the next
    when tests run in the same process.
    """
    yield
    app.dependency_overrides.clear()
