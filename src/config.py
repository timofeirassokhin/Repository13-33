from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PA_",
        case_sensitive=False,
    )

    # Twenty CRM (без PA_-префикса — общий с инфра-скриптами)
    twenty_api_url: str = Field(
        default="https://crm.13-33.pro",
        validation_alias="TWENTY_API_URL",
    )
    twenty_api_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias="TWENTY_API_KEY",
    )

    # Whisper (локальный транскрипционный сервис)
    whisper_url: str = Field(
        default="http://whisper:9000",
        validation_alias="WHISPER_URL",
    )

    # LiteLLM (роутер моделей для producer-агента)
    litellm_url: str = Field(
        default="http://litellm:4000",
        validation_alias="LITELLM_URL",
    )
    litellm_master_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias="LITELLM_MASTER_KEY",
    )

    # MemPalace (server-side архив 13-33)
    mempalace_url: str = Field(
        default="http://mempalace:8080",
        validation_alias="MEMPALACE_URL",
    )

    # Telegram
    telegram_bot_token: SecretStr
    telegram_allowed_user_ids: list[int] = []
    # Опциональный прокси для api.telegram.org (если хостинг режет outbound).
    # Поддерживается socks5://, socks5h://, http://, https:// (см. httpx).
    telegram_proxy: str = ""
    # ID Telegram-канала для постинга (формат: -100xxxxxxxxxx).
    # Бот должен быть админом канала с правом "Публиковать сообщения".
    telegram_channel_id: int = 0

    # Google OAuth2
    google_client_id: str = ""
    google_client_secret: SecretStr = SecretStr("")
    google_redirect_uri: str = "http://localhost:8443/oauth/callback"
    google_scopes: list[str] = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/documents",
    ]

    # Database
    db_path: str = "data/assistant.db"

    # Webhook server (for OAuth callback)
    webhook_host: str = "0.0.0.0"
    webhook_port: int = 8443

    # Logging
    log_level: str = "INFO"
    log_file: str = "data/logs/assistant.log"

    # File sorting
    default_sort_root: str = ""
    sort_by_type: bool = True
    sort_by_date: bool = False

    # Notes
    notes_folder_id: str = ""
