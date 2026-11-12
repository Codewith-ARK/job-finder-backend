from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, loaded from environment or .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Job Finder API"
    app_environment: Literal["development", "test", "production"] = "development"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./data/jobfinder.db"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    # Local-only convenience: allow the API's own origin and inject the CSRF
    # cookie into Swagger UI requests so /docs can exercise state changes.
    docs_testing_enabled: bool = False

    session_cookie: str = Field(default="jf_session", pattern=r"^[A-Za-z0-9_-]{1,64}$")
    csrf_cookie: str = Field(default="jf_csrf", pattern=r"^[A-Za-z0-9_-]{1,64}$")
    cookie_secure: bool = False
    session_days: int = 7

    demo_login_enabled: bool = False
    default_agency_slug: str = "northstar"
    seed_on_startup: bool = True
    referral_expiry_days: int = 7

    document_dir: str = "storage/documents"
    max_upload_bytes: int = 10 * 1024 * 1024
    max_json_bytes: int = Field(default=256 * 1024, ge=1024, le=1024 * 1024)
    requests_per_minute: int = Field(default=120, ge=1, le=10000)
    auth_requests_per_minute: int = Field(default=20, ge=1, le=1000)
    register_requests_per_minute: int = Field(default=5, ge=1, le=100)
    max_body_readers: int = Field(default=8, ge=1, le=64)
    body_timeout_seconds: int = Field(default=15, ge=1, le=60)
    max_documents_per_candidate: int = Field(default=10, ge=1, le=100)
    max_candidate_document_bytes: int = Field(default=50 * 1024 * 1024, ge=1, le=1024**3)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def document_path(self) -> Path:
        return Path(self.document_dir).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()


def configuration_problems(settings: Settings) -> list[tuple[str, str]]:
    """Audit settings that are easy to get wrong or unsafe outside local development.

    Returns ``(level, message)`` pairs. ``error`` entries must stop startup;
    ``warning`` entries are logged so the effective decision is visible.
    """
    problems: list[tuple[str, str]] = []
    raw_origins = settings.cors_origins.split(",")
    cleaned: list[str] = []
    seen: set[str] = set()

    for raw in raw_origins:
        value = raw.strip()
        if not value:
            problems.append(("warning", "CORS_ORIGINS contains an empty entry; it is ignored."))
            continue
        if value != raw:
            problems.append(
                (
                    "warning",
                    f"CORS_ORIGINS entry {value!r} has surrounding whitespace; "
                    "the trimmed value is used.",
                )
            )
        if value == "*":
            problems.append(
                (
                    "error",
                    "CORS_ORIGINS contains '*': the origin and CSRF allowlist would "
                    "accept every site. Use explicit origins.",
                )
            )
            continue
        if value.endswith("/"):
            problems.append(
                (
                    "warning",
                    f"CORS_ORIGINS entry {value!r} ends with '/'; origins are "
                    "scheme + host + port only.",
                )
            )
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            problems.append(
                (
                    "warning",
                    f"CORS_ORIGINS entry {value!r} does not look like an origin "
                    "(http://host:port).",
                )
            )
        if value in seen:
            problems.append(("warning", f"CORS_ORIGINS entry {value!r} is duplicated."))
        seen.add(value)
        cleaned.append(value)

    if not cleaned:
        problems.append(
            (
                "warning",
                "CORS_ORIGINS is empty: direct browser calls will be rejected. "
                "The same-origin Next.js proxy still works.",
            )
        )

    if settings.docs_testing_enabled:
        problems.append(
            (
                "warning",
                "DOCS_TESTING_ENABLED=true: Swagger UI may call state-changing routes "
                "from the API's own origin. Use only for local development.",
            )
        )
    if settings.demo_login_enabled:
        problems.append(("warning", "DEMO_LOGIN_ENABLED=true: demo persona sign-in is available."))
    if settings.seed_on_startup:
        problems.append(
            ("warning", "SEED_ON_STARTUP=true: an empty database is seeded at startup.")
        )
    if not settings.cookie_secure:
        problems.append(
            (
                "warning",
                "COOKIE_SECURE=false: session cookies may travel over plain HTTP. "
                "Set true behind HTTPS.",
            )
        )
    if settings.session_days > 30:
        problems.append(
            (
                "warning",
                f"SESSION_DAYS={settings.session_days} is longer than 30 days; "
                "consider a shorter session lifetime.",
            )
        )
    if settings.session_cookie == settings.csrf_cookie:
        problems.append(("error", "Session and CSRF cookies must have distinct names."))
    if settings.app_environment == "production":
        for unsafe, message in (
            (not settings.cookie_secure, "Production requires COOKIE_SECURE=true."),
            (settings.demo_login_enabled, "Production forbids DEMO_LOGIN_ENABLED=true."),
            (settings.seed_on_startup, "Production forbids SEED_ON_STARTUP=true."),
            (settings.docs_testing_enabled, "Production forbids DOCS_TESTING_ENABLED=true."),
            (
                not cleaned or any(not origin.startswith("https://") for origin in cleaned),
                "Production requires explicit HTTPS CORS origins.",
            ),
            (
                settings.session_days > 30 or settings.session_days < 1,
                "Production sessions must expire within 1 to 30 days.",
            ),
        ):
            if unsafe:
                problems.append(("error", message))
        problems = [
            ("error" if "CORS_ORIGINS" in message else level, message)
            for level, message in problems
        ]
    return problems
