from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    host: str = Field("0.0.0.0", validation_alias="TENDER_MONITOR_HOST")
    port: int = Field(8080, validation_alias="TENDER_MONITOR_PORT")
    database_url: str = Field(
        "postgresql://tender:tender@tender-db:5432/tender_monitor",
        validation_alias="TENDER_DATABASE_URL",
    )
    tenderland_base_url: str = Field("", validation_alias="TENDERLAND_BASE_URL")
    tenderland_api_token: str = Field("", validation_alias="TENDERLAND_API_TOKEN")
    twenty_api_base_url: str = Field(
        "http://twenty-server:3000",
        validation_alias="TWENTY_API_BASE_URL",
    )
    twenty_api_token: str = Field("", validation_alias="TWENTY_API_TOKEN")

    @property
    def integrations_ready(self) -> dict[str, bool]:
        return {
            "tenderland": bool(self.tenderland_base_url and self.tenderland_api_token),
            "twenty": bool(self.twenty_api_base_url and self.twenty_api_token),
        }

