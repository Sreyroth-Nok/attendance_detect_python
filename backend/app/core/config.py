"""Application settings loaded from environment variables (and optional .env files)."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Later files win: backend/.env overrides the project-root .env.
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Attendance Detection System - Student Management API"
    environment: str = Field(default="development", description="development | test | production")

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/attendance_db"

    # Comma-separated list of allowed browser origins.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # When set, write operations and CSV export require the header `X-API-Key: <value>`.
    # Must be set when ENVIRONMENT=production.
    admin_api_key: str = ""

    max_import_bytes: int = 2 * 1024 * 1024
    max_import_rows: int = 5000

    # Attendance sheet scanning (photo -> database).
    #   offline: free OCR + ink-colour detection on this computer (default, no API key)
    #   claude:  Claude vision via the Anthropic API (needs ANTHROPIC_API_KEY, paid)
    sheet_reader: str = "offline"
    anthropic_api_key: str = ""
    attendance_scan_model: str = "claude-opus-5-5"
    max_scan_bytes: int = 10 * 1024 * 1024
    # Khmer names (offline reader only): Tesseract with the Khmer language pack. Empty = auto-detect;
    # when Tesseract or khm.traineddata cannot be found, Khmer names are simply left blank.
    tesseract_cmd: str = ""
    tessdata_dir: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
