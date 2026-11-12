import logging
from contextlib import asynccontextmanager
from html import escape

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from .config import Settings, configuration_problems, get_settings
from .controllers import (
    auth_controller,
    candidates_controller,
    jobs_controller,
    platform_controller,
    referrals_controller,
    staff_controller,
)
from .database import SessionLocal
from .models import User
from .request_guards import RequestGuards
from .security import origin_allowed
from .seed import seed
from .services.errors import ServiceError

logger = logging.getLogger("jobfinder")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    if settings.app_environment == "production":
        with SessionLocal() as db:
            if db.scalar(select(User.id).where(User.is_demo.is_(True)).limit(1)):
                raise RuntimeError(
                    "Production cannot use a seeded demo database. "
                    "Provision a separate production database."
                )
    if settings.seed_on_startup:
        try:
            seed()
        except OperationalError:
            logger.warning("Database tables are missing. Run `uv run alembic upgrade head` first.")
    yield


def _docs_html(settings: Settings) -> str:
    """Swagger UI that echoes the CSRF cookie, for local API testing only."""
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{escape(settings.app_name)} — API docs</title>
    <link
      rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css"
    />
  </head>
  <body class="swagger-ui">
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
      window.ui = SwaggerUIBundle({{
        url: "/openapi.json",
        dom_id: "#swagger-ui",
        deepLinking: true,
        displayRequestDuration: true,
        requestInterceptor: (request) => {{
          const method = (request.method || "GET").toUpperCase();
          if (!["GET", "HEAD", "OPTIONS"].includes(method)) {{
            const match = document.cookie.match(
              /(?:^|; ){settings.csrf_cookie}=([^;]*)/
            );
            if (match) {{
              request.headers = request.headers || {{}};
              request.headers["X-CSRF-Token"] = decodeURIComponent(match[1]);
            }}
          }}
          return request;
        }},
      }});
    </script>
  </body>
</html>
"""


def create_app() -> FastAPI:
    settings = get_settings()
    problems = configuration_problems(settings)
    for level, message in problems:
        getattr(logger, level)("Configuration: %s", message)
    if any(level == "error" for level, _message in problems):
        raise RuntimeError("Unsafe configuration detected; see the log above.")
    if not problems:
        logger.info("Configuration audit passed: no unsafe settings detected.")
    logger.info(
        "Configuration: %d CORS origin(s); docs testing %s; cookie secure %s.",
        len(settings.cors_origin_list),
        "enabled" if settings.docs_testing_enabled else "disabled",
        "enabled" if settings.cookie_secure else "disabled",
    )

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None
        if settings.docs_testing_enabled or settings.app_environment == "production"
        else "/docs",
        openapi_url=None if settings.app_environment == "production" else "/openapi.json",
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def origin_guard(request: Request, call_next):
        if request.method not in {"GET", "HEAD", "OPTIONS"} and not origin_allowed(request):
            return JSONResponse({"detail": "This origin is not allowed."}, status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if not response.headers.get("content-type", "").startswith("text/html"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
            )
        return response

    if settings.docs_testing_enabled:

        @app.get("/docs", include_in_schema=False)
        def api_docs() -> HTMLResponse:
            return HTMLResponse(_docs_html(settings))

    @app.exception_handler(ServiceError)
    async def service_error_handler(_request: Request, error: ServiceError):
        return JSONResponse({"detail": error.message}, status_code=error.status_code)

    @app.get(f"{settings.api_prefix}/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    for router in (
        auth_controller.router,
        candidates_controller.router,
        staff_controller.router,
        jobs_controller.router,
        referrals_controller.router,
        platform_controller.router,
    ):
        app.include_router(router, prefix=settings.api_prefix)

    app.add_middleware(RequestGuards, state=app.state)
    return app


app = create_app()
