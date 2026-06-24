"""Settings loaded from .env (TL_ prefix)."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="TL_",
        extra="ignore",
    )

    api_key: str
    output_dir: Path = Path("Z:/tenders")
    base_url: str = "https://tenderland.ru"
    http_timeout: int = 120


def load_settings() -> Settings:
    """Load settings; .env is read from current working dir."""
    return Settings()  # type: ignore[call-arg]
