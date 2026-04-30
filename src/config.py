from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PA_",
        case_sensitive=False,
    )

    # Telegram
    telegram_bot_token: SecretStr
    telegram_allowed_user_ids: list[int] = []
    # Опциональный прокси для api.telegram.org (если хостинг режет outbound).
    # Поддерживается socks5://, socks5h://, http://, https:// (см. httpx).
    telegram_proxy: str = ""

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
