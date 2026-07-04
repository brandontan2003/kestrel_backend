import os
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.database_registry import get_sessionmaker

# picks ENV from system environment, defaults to "dev"
env = os.getenv("ENV", "dev")


class Settings(BaseSettings):
    ENV: str = "dev"

    DATABASE_URL: str = ""
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

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / f".env.{env}",
        extra="ignore",
        case_sensitive=True
    )


settings = Settings()


async def get_db():
    session_maker = get_sessionmaker()
    async with session_maker() as session:
        try:
            yield session
            # clean exit → commit
            await session.commit()
        except Exception:
            # any error → rollback
            await session.rollback()
            raise
