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
os.environ["DOCUMENT_DIR"] = (_TEMP / "documents").as_posix()

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app
from app.seed import seed


@pytest.fixture(autouse=True)
def fresh_database():
    if hasattr(app.state, "request_guard"):
        app.state.request_guard.reset()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed()
    yield


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
