import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from .config import get_settings
from .controllers import (
    auth_controller,
    candidates_controller,
    jobs_controller,
    platform_controller,
    staff_controller,
)
from .seed import seed
from .services.errors import ServiceError

logger = logging.getLogger("jobfinder")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    if settings.seed_on_startup:
        try:
            seed()
        except OperationalError:
            logger.warning("Database tables are missing. Run `uv run alembic upgrade head` first.")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
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
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin and origin not in settings.cors_origin_list:
                return JSONResponse({"detail": "This origin is not allowed."}, status_code=403)
        return await call_next(request)

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
        platform_controller.router,
    ):
        app.include_router(router, prefix=settings.api_prefix)

    return app


app = create_app()
