from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from app.config import get_settings
from app.database import SessionLocal
from app.main import app
from app.models import Agency, Application, AuthSession, Membership, User
from app.models.common import utcnow
from app.schemas.staff_schema import MemberPatch
from app.seed import MINIMAL_PDF
from app.services import auth_service, staff_service
from app.services.errors import Conflict

ORIGIN = {"Origin": "http://localhost:3000"}


def _csrf(client: TestClient) -> str:
    return client.cookies.get("jf_csrf")


def _suspend_agency(name: str = "Northstar Careers") -> str:
    admin = TestClient(app)
    persona = next(
        item
        for item in admin.get("/api/auth/demo-personas").json()
        if item["name"] == "Jules Lee"
    )
    assert (
        admin.post("/api/auth/demo-login", json={"personaId": persona["id"]}, headers=ORIGIN)
        .status_code
        == 200
    )
    agency = next(
        item
        for item in admin.get("/api/platform/workspace").json()["agencies"]
        if item["name"] == name
    )
    response = admin.patch(
        f"/api/platform/agencies/{agency['id']}",
        json={"status": "suspended"},
        headers={"X-CSRF-Token": _csrf(admin)},
    )
    assert response.status_code == 200, response.text
    return agency["id"]


def test_suspended_agency_login_is_rejected():
    _suspend_agency()
    probe = TestClient(app)
    response = probe.post(
        "/api/auth/login",
        json={"email": "sam@demo.example.com", "password": "Demo1234!"},
        headers=ORIGIN,
    )
    assert response.status_code == 403
    assert "jf_session" not in response.cookies


def test_referral_resolution_reports_suspended_agency():
    staff, csrf, _ = _sign_in_fixture()
    link = staff.post(
        "/api/referrals", json={}, headers={"X-CSRF-Token": csrf}
    ).json()
    _suspend_agency()

    probe = TestClient(app)
    resolved = probe.get(f"/api/referrals/{link['token']}").json()
    assert resolved["valid"] is False
    assert resolved["status"] == "inactive"

    registration = probe.post(
        "/api/auth/register",
        json={
            "name": "Suspended Candidate",
            "email": "suspended@example.com",
            "password": "Password123!",
            "referralToken": link["token"],
        },
        headers=ORIGIN,
    )
    assert registration.status_code == 409


def _sign_in_fixture():
    client = TestClient(app)
    persona = next(
        item
        for item in client.get("/api/auth/demo-personas").json()
        if item["name"] == "Sam Ali"
    )
    response = client.post(
        "/api/auth/demo-login", json={"personaId": persona["id"]}, headers=ORIGIN
    )
    assert response.status_code == 200, response.text
    return client, _csrf(client), response.json()


def test_deactivated_referrer_link_is_rejected(sign_in):
    staff, csrf, sam = _sign_in_fixture()
    link = staff.post("/api/referrals", json={}, headers={"X-CSRF-Token": csrf}).json()

    supervisor, scsrf, _ = sign_in("Noor Ahmed")
    deactivated = supervisor.patch(
        f"/api/staff/members/{sam['user']['id']}",
        json={"active": False},
        headers={"X-CSRF-Token": scsrf},
    )
    assert deactivated.status_code == 200

    probe = TestClient(app)
    assert probe.get(f"/api/referrals/{link['token']}").json()["status"] == "inactive"
    registration = probe.post(
        "/api/auth/register",
        json={
            "name": "Orphan Candidate",
            "email": "orphan@example.com",
            "password": "Password123!",
            "referralToken": link["token"],
        },
        headers=ORIGIN,
    )
    assert registration.status_code == 409


def test_last_supervisor_cannot_demote_themselves():
    with SessionLocal() as db:
        agency = Agency(name="Solo Agency", slug="solo-agency", region="Test")
        db.add(agency)
        db.flush()
        user = User(
            email="solo@example.com",
            name="Solo Supervisor",
            password_hash="unused",
            role="supervisor",
        )
        db.add(user)
        db.flush()
        db.add(Membership(user_id=user.id, agency_id=agency.id))
        db.commit()

        with pytest.raises(Conflict):
            staff_service.update_member(
                db, agency.id, user, user.id, MemberPatch(role="employee")
            )


def test_multi_agency_role_change_requires_platform_administration(sign_in):
    supervisor, csrf, noor = sign_in("Noor Ahmed")
    created = supervisor.post(
        "/api/staff/members",
        json={
            "name": "Second Supervisor",
            "email": "second.supervisor@example.com",
            "role": "supervisor",
            "team": "Candidate success",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 200, created.text

    other = TestClient(app)
    login = other.post(
        "/api/auth/login",
        json={
            "email": "second.supervisor@example.com",
            "password": created.json()["temporaryPassword"],
        },
        headers=ORIGIN,
    )
    assert login.status_code == 200, login.text

    response = other.patch(
        f"/api/staff/members/{noor['user']['id']}",
        json={"role": "employee"},
        headers={"X-CSRF-Token": _csrf(other)},
    )
    assert response.status_code == 403


def test_blank_and_oversized_inputs_are_rejected(sign_in):
    probe = TestClient(app)
    blank_name = probe.post(
        "/api/auth/register",
        json={"name": "   ", "email": "blank@example.com", "password": "Password123!"},
        headers=ORIGIN,
    )
    assert blank_name.status_code == 422

    supervisor, csrf, _ = sign_in("Noor Ahmed")
    base_job = {
        "title": "Designer",
        "company": "Northstar",
        "location": "Remote",
        "workType": "Remote",
    }
    headers = {"X-CSRF-Token": csrf}
    assert (
        supervisor.post(
            "/api/jobs", json={**base_job, "title": "   "}, headers=headers
        ).status_code
        == 422
    )
    assert (
        supervisor.post(
            "/api/jobs", json={**base_job, "tags": ["x" * 41]}, headers=headers
        ).status_code
        == 422
    )


def test_readiness_endpoint_reports_database():
    response = TestClient(app).get("/api/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_expired_sessions_are_purged():
    with SessionLocal() as db:
        sam = db.scalar(select(User).where(User.email == "sam@demo.example.com"))
        expired = AuthSession(
            user_id=sam.id,
            token_hash="a" * 64,
            csrf_hash="b" * 64,
            expires_at=utcnow() - timedelta(days=10),
        )
        active = AuthSession(
            user_id=sam.id,
            token_hash="c" * 64,
            csrf_hash="d" * 64,
            expires_at=utcnow() + timedelta(days=1),
        )
        db.add_all([expired, active])
        db.commit()
        active_id = active.id

        assert auth_service.purge_sessions(db, 7) == 1
        assert db.get(AuthSession, active_id) is not None


def test_deleting_the_last_document_invalidates_onboarding(sign_in, complete_onboarding):
    candidate, csrf, _ = sign_in("Aya Khan")
    workspace = complete_onboarding(candidate, csrf)
    document = workspace["documents"][0]

    removed = candidate.delete(
        f"/api/candidates/me/documents/{document['id']}",
        headers={"X-CSRF-Token": csrf},
    )
    assert removed.status_code == 200
    assert removed.json()["onboardingComplete"] is False
    documents_step = next(
        step for step in removed.json()["onboarding"] if step["id"] == "documents"
    )
    assert documents_step["status"] != "complete"


def test_onboarding_child_ids_are_stable():
    client = TestClient(app)
    registered = client.post(
        "/api/auth/register",
        json={
            "name": "Stable Records",
            "email": "stable@example.com",
            "password": "Password123!",
        },
        headers=ORIGIN,
    )
    assert registered.status_code == 200, registered.text
    csrf = _csrf(client)
    headers = {"X-CSRF-Token": csrf}
    assert (
        client.put(
            "/api/candidates/me/onboarding/personal",
            json={"phone": "+1 555 0100", "location": "Remote", "headline": "Designer"},
            headers=headers,
        ).status_code
        == 200
    )
    assert (
        client.post("/api/candidates/me/onboarding/personal/complete", headers=headers).status_code
        == 200
    )

    payload = {
        "currentTitle": "Designer",
        "experienceLevel": "Mid",
        "skills": ["Figma"],
        "experiences": [
            {
                "company": "Acme",
                "title": "Designer",
                "startDate": "2020-01",
                "current": True,
            }
        ],
        "preferences": {"workType": "Remote", "preferredLocation": "Remote"},
    }
    first = client.put(
        "/api/candidates/me/onboarding/professional", json=payload, headers=headers
    )
    assert first.status_code == 200, first.text
    experience_id = first.json()["experiences"][0]["id"]

    payload["experiences"][0]["id"] = experience_id
    second = client.put(
        "/api/candidates/me/onboarding/professional", json=payload, headers=headers
    )
    assert second.status_code == 200, second.text
    assert second.json()["experiences"][0]["id"] == experience_id


def test_failed_logins_lock_the_account_without_breaking_successful_ones():
    client = TestClient(app)
    for _ in range(8):
        response = client.post(
            "/api/auth/login",
            json={"email": "sam@demo.example.com", "password": "WrongPassword!"},
            headers=ORIGIN,
        )
        assert response.status_code == 401

    locked = client.post(
        "/api/auth/login",
        json={"email": "sam@demo.example.com", "password": "Demo1234!"},
        headers=ORIGIN,
    )
    assert locked.status_code == 429
    assert int(locked.headers["Retry-After"]) > 0


def test_applying_requires_complete_onboarding(client):
    registered = client.post(
        "/api/auth/register",
        json={
            "name": "Early Applicant",
            "email": "early.applicant@example.com",
            "password": "Password123!",
        },
        headers=ORIGIN,
    )
    assert registered.status_code == 200, registered.text
    candidate_id = registered.json()["user"]["id"]
    csrf = _csrf(client)

    job = client.get("/api/jobs/workspace").json()["jobs"][0]
    response = client.post(
        f"/api/jobs/{job['id']}/apply", headers={"X-CSRF-Token": csrf}
    )
    assert response.status_code == 409
    with SessionLocal() as db:
        assert (
            db.scalar(
                select(Application).where(Application.candidate_id == candidate_id)
            )
            is None
        )


def test_unexpected_integrity_error_returns_conflict(monkeypatch):
    def explode(*_args, **_kwargs):
        raise IntegrityError("INSERT INTO users", {}, Exception("duplicate key"))

    monkeypatch.setattr(auth_service, "register", explode)
    response = TestClient(app).post(
        "/api/auth/register",
        json={
            "name": "Racing Duplicate",
            "email": "racing@example.com",
            "password": "Password123!",
        },
        headers=ORIGIN,
    )
    assert response.status_code == 409
    assert response.json()["detail"]


def test_upload_removes_the_file_when_the_database_write_fails(sign_in, monkeypatch):
    client, csrf, session = sign_in("Aya Khan")

    def fail(_self):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(DbSession, "commit", fail)
    with pytest.raises(RuntimeError):
        client.post(
            "/api/candidates/me/documents",
            files={"file": ("cv.pdf", MINIMAL_PDF, "application/pdf")},
            headers={"X-CSRF-Token": csrf},
        )

    folder = Path(get_settings().document_dir) / session["user"]["id"]
    assert not folder.exists() or not any(folder.iterdir())
