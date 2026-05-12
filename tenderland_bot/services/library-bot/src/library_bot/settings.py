"""Конфиг бота. Все значения через env (с префиксом GLUVEX_LIBRARY_BOT_)."""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GLUVEX_LIBRARY_BOT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # === Telegram ===
    token: str = Field(min_length=20)
    username: str = "gluvexlibrary_bot"
    # comma-separated Telegram user IDs (whitelist). Empty = открыто всем.
    allowed_ids: str = ""
    # SOCKS5 прокси для outbound к api.telegram.org (RU-VPS блок).
    # Внутри docker-сети — `socks5://warp:1080`.
    proxy: str = "socks5://warp:1080"

    # === Postgres app-db ===
    pg_host: str = "app-db"
    pg_port: int = 5432
    pg_user: str = "gluvex_app"
    pg_password: str = Field(default="", min_length=0)
    pg_database: str = "gluvex_documents"
    tenant_id: str = "11111111-1111-1111-1111-111111111111"

    # === MinIO ===
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket_brochures: str = "product-brochures"
    minio_secure: bool = False

    # === LiteLLM (intent parsing) ===
    litellm_base_url: str = "http://litellm:4000"
    litellm_master_key: str = ""
    litellm_intent_model: str = "creative"      # alias из litellm-config.yaml
    litellm_intent_temp: float = 0.1
    litellm_intent_max_tokens: int = 600

    # === Whisper ASR (local, in-cluster) ===
    whisper_url: str = "http://whisper-asr:9000"
    whisper_language: str = "ru"
    whisper_timeout_sec: int = 60

    # === Поведение ===
    default_search_limit: int = 10
    max_pdfs_per_response: int = 5     # ограничение чтобы не залить чат
    log_level: str = "INFO"

    @property
    def allowed_id_set(self) -> set[int]:
        return {int(x.strip()) for x in self.allowed_ids.split(",") if x.strip()}

    @property
    def pg_dsn(self) -> str:
        return (
            f"postgresql://{self.pg_user}:{self.pg_password}"
            f"@{self.pg_host}:{self.pg_port}/{self.pg_database}"
        )
