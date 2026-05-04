from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GLUE_", extra="ignore")

    port: int = 8000
    webhook_secret: str = ""


class TwentySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TWENTY_TR_", extra="ignore")

    api_url: str = ""
    api_key: str = ""


class RobokassaSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ROBOKASSA_", extra="ignore")

    merchant_login: str = ""
    pass1: str = ""
    pass2: str = ""
    test_mode: int = 1


class ListmonkSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    listmonk_url: str = "http://listmonk:9000"
    listmonk_admin_user: str = "admin"
    listmonk_admin_password: str = ""


def load() -> tuple[Settings, TwentySettings, RobokassaSettings, ListmonkSettings]:
    return Settings(), TwentySettings(), RobokassaSettings(), ListmonkSettings()
