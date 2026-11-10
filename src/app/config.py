from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, loaded from environment or .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Job Finder API"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./data/jobfinder.db"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    session_cookie: str = "jf_session"
    csrf_cookie: str = "jf_csrf"
    cookie_secure: bool = False
    session_days: int = 7

    demo_login_enabled: bool = False
    default_agency_slug: str = "northstar"
    seed_on_startup: bool = True

    document_dir: str = "storage/documents"
    max_upload_bytes: int = 10 * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def document_path(self) -> Path:
        return Path(self.document_dir).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
