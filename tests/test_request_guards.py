import asyncio

from app.main import app


def test_oversized_json_rejected_before_validation(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "max_json_bytes", 128, raising=False)
    response = client.post("/api/auth/register", content=b"x" * 129)
    assert response.status_code == 413


def test_login_attempts_are_limited(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "auth_requests_per_minute", 2, raising=False)
    for _ in range(2):
        assert client.post("/api/auth/login", json={}).status_code == 422
    response = client.post("/api/auth/login", json={})
    assert response.status_code == 429
    assert int(response.headers["retry-after"]) > 0


def test_unauthorized_upload_body_is_not_read():
    reads = []
    messages = []

    async def receive():
        reads.append(True)
        return {
            "type": "http.request",
            "body": (
                b'--audit\r\nContent-Disposition: form-data; name="file"; filename="x.pdf"\r\n'
                b"Content-Type: application/pdf\r\n\r\n%PDF\r\n--audit--\r\n"
            ),
        }

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/candidates/me/documents",
        "raw_path": b"/api/candidates/me/documents",
        "query_string": b"",
        "headers": [(b"content-type", b"multipart/form-data; boundary=audit")],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
    }
    asyncio.run(app(scope, receive, send))
    assert messages[0]["status"] == 401
    assert reads == []


def test_forged_upload_session_is_denied_before_parsing(client):
    client.cookies.set("jf_session", "forged-session")
    response = client.post("/api/candidates/me/documents", content=b"invalid multipart")
    assert response.status_code == 401


def test_forwarded_header_does_not_bypass_rate_limit(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "auth_requests_per_minute", 1)
    assert (
        client.post("/api/auth/login", json={}, headers={"X-Forwarded-For": "1.2.3.4"}).status_code
        == 422
    )
    assert (
        client.post("/api/auth/login", json={}, headers={"X-Forwarded-For": "5.6.7.8"}).status_code
        == 429
    )


def test_chunked_body_limit_without_content_length(monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "max_json_bytes", 128)
    messages = []
    chunks = iter([b"x" * 100, b"x" * 100])

    async def receive():
        return {"type": "http.request", "body": next(chunks), "more_body": True}

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/auth/register",
        "raw_path": b"/api/auth/register",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
    }
    asyncio.run(app(scope, receive, send))
    assert messages[0]["status"] == 413
