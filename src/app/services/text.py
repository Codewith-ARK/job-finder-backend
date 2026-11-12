"""Bounded derived text for log columns."""

MAX_ACTIVITY_TITLE = 200
MAX_ACTIVITY_DETAIL = 300


def clip(value: str, limit: int) -> str:
    """Keep derived text within its database column without a silent truncation marker."""
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)] + "..."
