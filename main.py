"""ASGI entry point for `uv run fastapi dev main.py` and uvicorn."""

from app.main import app

__all__ = ["app"]
