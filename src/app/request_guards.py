import asyncio
import math
import threading
import time
from collections import deque

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse

from .config import get_settings
from .security import origin_allowed, validate_upload_request
from .services.errors import ServiceError


class RequestGuards:
    """Bound request work before parsing. Limits are shared within one process.

    Multiple workers/replicas also require shared enforcement at the gateway.
    Forwarded client addresses must be validated by the ASGI server's proxy policy.
    """

    def __init__(self, app, state):
        self.app = app
        self.buckets = {}
        self.lock = threading.Lock()
        self.readers = threading.BoundedSemaphore(get_settings().max_body_readers)
        state.request_guard = self

    def reset(self):
        with self.lock:
            self.buckets.clear()

    def allowed(self, key, limit):
        now = time.monotonic()
        with self.lock:
            if key not in self.buckets:
                if len(self.buckets) >= 4096:
                    self.buckets = {k: v for k, v in self.buckets.items() if v and v[-1] > now - 60}
                if len(self.buckets) >= 4096:
                    return 60
                self.buckets[key] = deque()
            bucket = self.buckets[key]
            while bucket and bucket[0] <= now - 60:
                bucket.popleft()
            if len(bucket) >= limit:
                return max(1, math.ceil(60 - (now - bucket[0])))
            bucket.append(now)
        return 0

    @staticmethod
    async def reject(scope, receive, send, code, detail, retry=None):
        headers = {
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "no-referrer",
        }
        if retry:
            headers["Retry-After"] = str(retry)
        await JSONResponse({"detail": detail}, status_code=code, headers=headers)(
            scope, receive, send
        )

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        settings = get_settings()
        request = Request(scope)
        prefix = settings.api_prefix
        path = scope["path"].rstrip("/")
        mutation = scope["method"] not in {"GET", "HEAD", "OPTIONS"}
        if mutation and not origin_allowed(request):
            return await self.reject(scope, receive, send, 403, "This origin is not allowed.")
        if path.startswith(prefix + "/") and scope["method"] != "OPTIONS":
            address = scope.get("client") or ("unknown", 0)
            retry = self.allowed(("ip", address[0]), settings.requests_per_minute)
            if mutation and path.startswith(prefix + "/auth/"):
                limit = (
                    settings.register_requests_per_minute
                    if path == prefix + "/auth/register"
                    else settings.auth_requests_per_minute
                )
                category = "registration" if path == prefix + "/auth/register" else "auth"
                retry = retry or self.allowed((category, address[0]), limit)
            if retry:
                return await self.reject(
                    scope, receive, send, 429, "Too many requests. Try again later.", retry
                )
        upload = path == prefix + "/candidates/me/documents" and scope["method"] == "POST"
        if upload:
            try:
                await run_in_threadpool(validate_upload_request, request)
            except ServiceError as error:
                return await self.reject(scope, receive, send, error.status_code, error.message)
        if not mutation:
            return await self.app(scope, receive, send)
        maximum = settings.max_upload_bytes + 65536 if upload else settings.max_json_bytes
        try:
            length = int(request.headers.get("content-length", "0"))
        except ValueError:
            return await self.reject(scope, receive, send, 400, "Invalid Content-Length.")
        if length < 0 or length > maximum:
            return await self.reject(scope, receive, send, 413, "Request body is too large.")
        if not self.readers.acquire(blocking=False):
            return await self.reject(scope, receive, send, 503, "Server busy. Try again later.", 1)
        try:

            async def read_body():
                body = bytearray()
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return None
                    chunk = message.get("body", b"")
                    if len(body) + len(chunk) > maximum:
                        raise OverflowError
                    body.extend(chunk)
                    if not message.get("more_body", False):
                        return bytes(body)
                    await asyncio.sleep(0)

            try:
                body = await asyncio.wait_for(read_body(), settings.body_timeout_seconds)
            except OverflowError:
                return await self.reject(scope, receive, send, 413, "Request body is too large.")
            except TimeoutError:
                return await self.reject(scope, receive, send, 408, "Request body timed out.")
            if body is None:
                return
            delivered = False

            async def replay():
                nonlocal delivered
                if delivered:
                    return await receive()
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}

            await self.app(scope, replay, send)
        finally:
            self.readers.release()
