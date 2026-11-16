import os
import tempfile
from pathlib import Path

_TEMP = Path(tempfile.mkdtemp(prefix="jobfinder-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_TEMP / 'test.db').as_posix()}"
os.environ["APP_ENVIRONMENT"] = "test"
os.environ["DEMO_LOGIN_ENABLED"] = "true"
os.environ["SEED_ON_STARTUP"] = "false"
os.environ["COOKIE_SECURE"] = "false"
os.environ["DOCS_TESTING_ENABLED"] = "true"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app
from app.seed import MINIMAL_PDF, seed
from app.services import storage
from app.throttle import login_throttle


@pytest.fixture
def fake_blob(monkeypatch):
    blobs: dict[str, tuple[bytes, str]] = {}

    def upload(pathname: str, data: bytes, content_type: str) -> str:
        blobs[pathname] = (data, content_type)
        return pathname

    def download(pathname: str) -> tuple[bytes, str]:
        return blobs[pathname]

    def remove(pathname: str) -> None:
        blobs.pop(pathname, None)

    monkeypatch.setattr(storage, "upload", upload)
    monkeypatch.setattr(storage, "download", download)
    monkeypatch.setattr(storage, "remove", remove)
    return blobs


@pytest.fixture(autouse=True)
def fresh_database(fake_blob):
    if hasattr(app.state, "request_guard"):
        app.state.request_guard.reset()
    login_throttle.reset()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed()
    yield


@pytest.fixture
def valid_pdf() -> bytes:
    return MINIMAL_PDF


@pytest.fixture
def complete_onboarding():
    def _complete(client: TestClient, csrf: str) -> None:
        headers = {"X-CSRF-Token": csrf}
        steps = [
            (
                "personal",
                {
                    "phone": "+1 555 0100",
                    "location": "Remote",
                    "headline": "Product designer",
                    "summary": "Designer with product experience.",
                },
            ),
            (
                "professional",
                {
                    "currentTitle": "Product designer",
                    "experienceLevel": "Mid",
                    "skills": ["Figma"],
                    "preferences": {"workType": "Remote", "preferredLocation": "Remote"},
                },
            ),
            (
                "academic",
                {
                    "education": [
                        {
                            "institution": "Test University",
                            "degree": "BSc",
                            "startYear": 2018,
                        }
                    ]
                },
            ),
        ]
        for step, payload in steps:
            saved = client.put(
                f"/api/candidates/me/onboarding/{step}", json=payload, headers=headers
            )
            assert saved.status_code == 200, saved.text
            completed = client.post(
                f"/api/candidates/me/onboarding/{step}/complete", headers=headers
            )
            assert completed.status_code == 200, completed.text
        uploaded = client.post(
            "/api/candidates/me/documents",
            files={"file": ("cv.pdf", MINIMAL_PDF, "application/pdf")},
            headers=headers,
        )
        assert uploaded.status_code == 200, uploaded.text
        finished = client.post("/api/candidates/me/onboarding/documents/complete", headers=headers)
        assert finished.status_code == 200, finished.text
        assert finished.json()["onboardingComplete"] is True
        return finished.json()

    return _complete


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sign_in():
    def _sign_in(name: str, agency_id: str | None = None):
        client = TestClient(app)
        personas = client.get("/api/auth/demo-personas").json()
        persona = next(item for item in personas if item["name"] == name)
        response = client.post(
            "/api/auth/demo-login",
            json={"personaId": persona["id"]},
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 200, response.text
        csrf = client.cookies.get("jf_csrf")
        if agency_id:
            switch = client.post(
                "/api/auth/context",
                json={"agencyId": agency_id},
                headers={"X-CSRF-Token": csrf},
            )
            assert switch.status_code == 200, switch.text
        return client, csrf, response.json()

    return _sign_in
