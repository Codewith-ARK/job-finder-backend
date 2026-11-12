from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, loaded from environment or .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Job Finder API"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./data/jobfinder.db"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    # Local-only convenience: allow the API's own origin and inject the CSRF
    # cookie into Swagger UI requests so /docs can exercise state changes.
    docs_testing_enabled: bool = False

    session_cookie: str = "jf_session"
    csrf_cookie: str = "jf_csrf"
    cookie_secure: bool = False
    session_days: int = 7

    demo_login_enabled: bool = False
    default_agency_slug: str = "northstar"
    seed_on_startup: bool = True
    referral_expiry_days: int = 7

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
            problems.append(
                ("warning", "CORS_ORIGINS contains an empty entry; it is ignored.")
            )
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
        problems.append(
            ("warning", "DEMO_LOGIN_ENABLED=true: demo persona sign-in is available.")
        )
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
    return problems
