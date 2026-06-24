"""Settings for catalog-crawler — все из env."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Postgres (gluvex_documents)
    pg_host: str = "app-db"
    pg_port: int = 5432
    pg_db: str = "gluvex_documents"
    pg_user: str = "gluvex_app"
    pg_password: str = ""

    # MinIO
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_secure: bool = False
    minio_raw_bucket: str = "raw-documents"
    minio_brochures_bucket: str = "product-brochures"

    # Crawler params
    rate_limit_rps: float = 1.5
    user_agent: str = "GluvexCatalogCrawler/0.1 (+https://gluvex.com)"
    request_timeout: int = 30
    max_retries: int = 3

    @property
    def pg_dsn(self) -> str:
        return f"postgresql://{self.pg_user}:{self.pg_password}@{self.pg_host}:{self.pg_port}/{self.pg_db}"


settings = Settings()
