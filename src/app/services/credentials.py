import hashlib
import secrets

from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()


def hash_secret(value: str) -> str:
    """Hash a high-entropy opaque token for storage and lookup."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def new_secret() -> str:
    return secrets.token_urlsafe(32)


def hash_password(value: str) -> str:
    return password_hash.hash(value)


def verify_password(value: str, stored: str) -> bool:
    return password_hash.verify(value, stored)
