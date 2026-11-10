from datetime import UTC, datetime
from uuid import uuid4


def new_id() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    # Naive UTC keeps SQLite and PostgreSQL comparisons identical.
    return datetime.now(UTC).replace(tzinfo=None)
