import os
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

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

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / f".env.{env}",
        extra="ignore",
        case_sensitive=True
    )


settings = Settings()
