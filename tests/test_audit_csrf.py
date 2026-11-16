from fastapi.testclient import TestClient

from app.main import app


def test_non_ascii_csrf_is_denied(sign_in):
    candidate, _, _ = sign_in("Aya Khan")
    with TestClient(app, raise_server_exceptions=False, cookies=dict(candidate.cookies)) as client:
        response = client.post(
            "/api/candidates/me/onboarding/missing/complete",
            headers=[(b"X-CSRF-Token", b"\xff")],
        )
        assert response.status_code == 403
