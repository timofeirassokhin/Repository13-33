from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TR_BOT_", extra="ignore")

    token: str = Field(min_length=10)
    allowed_admin_ids: list[int] = Field(default_factory=list)


class GlueSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    glue_base_url: str = "http://glue:8000"
    glue_webhook_secret: str = ""
    mempalace_url: str = "http://mempalace:8080"


def load() -> tuple[Settings, GlueSettings]:
    return Settings(), GlueSettings()
