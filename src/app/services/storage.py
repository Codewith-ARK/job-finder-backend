import os

from vercel.blob import sync as blob

from ..config import get_settings


def _hydrate_blob_environment() -> None:
    """Expose credentials loaded from .env to the Blob SDK."""
    settings = get_settings()
    if settings.blob_store_id:
        os.environ.setdefault("BLOB_STORE_ID", settings.blob_store_id)
    if settings.blob_read_write_token:
        os.environ.setdefault("BLOB_READ_WRITE_TOKEN", settings.blob_read_write_token)


def upload(pathname: str, data: bytes, content_type: str) -> str:
    _hydrate_blob_environment()
    blob.put_blob(pathname, data, access="private", content_type=content_type)
    return pathname  # DB mein pathname save karo, URL nahi


def download(pathname: str) -> tuple[bytes, str | None]:
    _hydrate_blob_environment()
    r = blob.get_blob(pathname, access="private")
    return r.body, r.metadata.content_type


def remove(pathname: str) -> None:
    _hydrate_blob_environment()
    blob.delete_blob(pathname)
