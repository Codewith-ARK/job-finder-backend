"""Failure-based login throttling.

Only failed credentials count, so an attacker cannot lock a real account out by
sending successful-looking requests. State is process-local: a deployment with
more than one API replica must also enforce per-IP/account limits at its edge.
"""

import threading
import time
from collections import deque
from hashlib import sha256


class FailureThrottle:
    def __init__(self) -> None:
        self._failures: dict[str, deque[float]] = {}
        self._locked_until: dict[str, float] = {}
        self._lock = threading.Lock()

    @staticmethod
    def key(email: str) -> str:
        return sha256(email.strip().casefold().encode()).hexdigest()

    def retry_after(self, key: str) -> int:
        """Seconds until another attempt is allowed, or 0 when it is allowed."""
        now = time.monotonic()
        with self._lock:
            locked_until = self._locked_until.get(key, 0.0)
            if locked_until > now:
                return max(1, int(locked_until - now + 0.999))
            self._locked_until.pop(key, None)
            return 0

    def fail(self, key: str, limit: int, lockout_seconds: int) -> int:
        """Record a failed attempt and return the lockout in seconds, if any."""
        now = time.monotonic()
        with self._lock:
            bucket = self._failures.setdefault(key, deque())
            while bucket and bucket[0] <= now - lockout_seconds:
                bucket.popleft()
            bucket.append(now)
            if len(bucket) < limit:
                return 0
            bucket.clear()
            self._locked_until[key] = now + lockout_seconds
            return lockout_seconds

    def success(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
            self._locked_until.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()
            self._locked_until.clear()


login_throttle = FailureThrottle()
