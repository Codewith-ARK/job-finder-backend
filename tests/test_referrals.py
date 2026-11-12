from fastapi.testclient import TestClient

from app.main import app
from app.seed import DEMO_REFERRAL_TOKENS

ORIGIN = {"Origin": "http://localhost:3000"}
ACTIVE_TOKEN = DEMO_REFERRAL_TOKENS["active"]
EXPIRED_TOKEN = DEMO_REFERRAL_TOKENS["expired"]


def _register(client: TestClient, email: str, token: str | None = None):
    payload = {"name": "Referred Candidate", "email": email, "password": "Password123!"}
    if token:
        payload["referralToken"] = token
    return client.post("/api/auth/register", json=payload, headers=ORIGIN)


def test_individual_registration_has_no_agency(client):
    response = _register(client, "independent@example.com")
    assert response.status_code == 200, response.text
    session = response.json()
    assert session["user"]["role"] == "candidate"
    assert session["agency"] is None
    assert session["user"]["agencies"] == []

    workspace = client.get("/api/candidates/me").json()
    assert workspace["profile"]["name"] == "Referred Candidate"
    assert workspace["referral"] is None
    assert [step["id"] for step in workspace["onboarding"]] == [
        "personal",
        "professional",
        "academic",
        "documents",
    ]
    assert workspace["onboarding"][0]["status"] == "next"

    jobs = client.get("/api/jobs/workspace").json()["jobs"]
    assert {"Content Designer", "Product Designer"} <= {job["title"] for job in jobs}

    # Staff never see independent candidates, even after an application.
    staff, _csrf, _ = _sign_in("Sam Ali")
    names = {item["name"] for item in staff.get("/api/staff/workspace").json()["candidates"]}
    assert "Referred Candidate" not in names


def _sign_in(name: str, agency_index: int | None = None):
    client = TestClient(app)
    personas = client.get("/api/auth/demo-personas").json()
    persona = next(item for item in personas if item["name"] == name)
    response = client.post(
        "/api/auth/demo-login", json={"personaId": persona["id"]}, headers=ORIGIN
    )
    assert response.status_code == 200, response.text
    csrf = client.cookies.get("jf_csrf")
    if agency_index is not None:
        agency_id = response.json()["user"]["agencies"][agency_index]["id"]
        switched = client.post(
            "/api/auth/context",
            json={"agencyId": agency_id},
            headers={"X-CSRF-Token": csrf},
        )
        assert switched.status_code == 200, switched.text
    return client, csrf, response.json()


def _login(email: str):
    client = TestClient(app)
    response = client.post(
        "/api/auth/login", json={"email": email, "password": "Demo1234!"}, headers=ORIGIN
    )
    assert response.status_code == 200, response.text
    return client, client.cookies.get("jf_csrf"), response.json()


def test_referral_resolve_and_signup_assigns_agency(client):
    resolved = client.get(f"/api/referrals/{ACTIVE_TOKEN}")
    assert resolved.status_code == 200
    assert resolved.json()["valid"] is True
    assert resolved.json()["agencyName"] == "Northstar Careers"
    assert resolved.json()["referrerName"] == "Sam Ali"

    response = _register(client, "referred@example.com", ACTIVE_TOKEN)
    assert response.status_code == 200, response.text
    session = response.json()
    assert session["agency"]["name"] == "Northstar Careers"
    assert [agency["name"] for agency in session["user"]["agencies"]] == ["Northstar Careers"]

    workspace = client.get("/api/candidates/me").json()
    assert workspace["referral"] == {
        "agencyName": "Northstar Careers",
        "referrerName": "Sam Ali",
        "label": "Product design referrals",
    }

    # Only the referring agency's roles are visible to a referred candidate.
    jobs = client.get("/api/jobs/workspace").json()["jobs"]
    assert {job["agencyName"] for job in jobs} == {"Northstar Careers"}

    staff, _csrf, _ = _sign_in("Sam Ali")
    staff_workspace = staff.get("/api/staff/workspace").json()
    referred = next(
        item for item in staff_workspace["candidates"] if item["name"] == "Referred Candidate"
    )
    sam = next(member for member in staff_workspace["teamMembers"] if member["name"] == "Sam Ali")
    assert referred["assignedTo"] == sam["id"]

    # The referral context survives a logout/login cycle.
    assert client.post(
        "/api/auth/logout", headers={"X-CSRF-Token": client.cookies.get("jf_csrf")}
    ).status_code == 204
    login = client.post(
        "/api/auth/login",
        json={"email": "referred@example.com", "password": "Password123!"},
        headers=ORIGIN,
    )
    assert login.status_code == 200
    assert login.json()["agency"]["name"] == "Northstar Careers"
    assert client.get("/api/candidates/me").json()["referral"]["agencyName"] == "Northstar Careers"


def test_referral_link_is_single_use(client):
    assert _register(client, "first@example.com", ACTIVE_TOKEN).status_code == 200
    second = TestClient(app)
    duplicate = _register(second, "second@example.com", ACTIVE_TOKEN)
    assert duplicate.status_code == 409
    assert "already been used" in duplicate.json()["detail"]

    resolved = second.get(f"/api/referrals/{ACTIVE_TOKEN}").json()
    assert resolved["valid"] is False
    assert resolved["status"] == "used"


def test_expired_and_unknown_referrals_are_rejected(client):
    expired = client.get(f"/api/referrals/{EXPIRED_TOKEN}").json()
    assert expired["valid"] is False
    assert expired["status"] == "expired"
    assert _register(client, "expired@example.com", EXPIRED_TOKEN).status_code == 409

    unknown = client.get("/api/referrals/not-a-real-token").json()
    assert unknown["valid"] is False
    assert unknown["status"] == "unknown"
    assert _register(client, "unknown@example.com", "not-a-real-token").status_code == 409


def test_staff_referral_management_and_scope(sign_in):
    employee, csrf, _ = _sign_in("Sam Ali")
    created = employee.post(
        "/api/referrals",
        json={"label": "Campus fair", "expiresInDays": 3},
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 200, created.text
    link = created.json()["link"]
    token = created.json()["token"]
    assert created.json()["path"] == f"/join/{token}"
    assert link["status"] == "active"
    assert employee.get(f"/api/referrals/{token}").json()["valid"] is True

    listed = employee.get("/api/referrals").json()
    assert any(item["id"] == link["id"] for item in listed)

    # Another employee in the same agency cannot see or revoke it.
    olivia, ocsrf, _ = _login("olivia@northstar.example.com")
    assert all(item["id"] != link["id"] for item in olivia.get("/api/referrals").json())
    denied = olivia.delete(f"/api/referrals/{link['id']}", headers={"X-CSRF-Token": ocsrf})
    assert denied.status_code == 403

    # A supervisor in another agency cannot reach it either.
    supervisor, scsrf, _ = _sign_in("Noor Ahmed", agency_index=1)
    cross = supervisor.delete(f"/api/referrals/{link['id']}", headers={"X-CSRF-Token": scsrf})
    assert cross.status_code == 404

    revoked = employee.delete(f"/api/referrals/{link['id']}", headers={"X-CSRF-Token": csrf})
    assert revoked.status_code == 200
    assert next(item for item in revoked.json() if item["id"] == link["id"])["status"] == "revoked"
    assert employee.get(f"/api/referrals/{token}").json()["status"] == "revoked"

    use = TestClient(app)
    assert _register(use, "revoked@example.com", token).status_code == 409


def test_individual_application_reaches_the_job_agency(client):
    assert _register(client, "applicant@example.com").status_code == 200
    csrf = client.cookies.get("jf_csrf")
    job = next(
        job
        for job in client.get("/api/jobs/workspace").json()["jobs"]
        if job["title"] == "Content Designer"
    )
    applied = client.post(f"/api/jobs/{job['id']}/apply", headers={"X-CSRF-Token": csrf})
    assert applied.status_code == 200, applied.text
    application = next(
        item for item in applied.json()["applications"] if item["jobId"] == job["id"]
    )
    assert application["agencyName"] == "Harbor Talent"
    assert application["jobTitle"] == "Content Designer"

    # Harbor staff see the application but not the independent candidate profile.
    harbor = TestClient(app)
    login = harbor.post(
        "/api/auth/login",
        json={"email": "elena@harbor.example.com", "password": "Demo1234!"},
        headers=ORIGIN,
    )
    assert login.status_code == 200
    workspace = harbor.get("/api/jobs/workspace").json()
    assert any(item["id"] == application["id"] for item in workspace["applications"])
    staff_candidates = harbor.get("/api/staff/workspace").json()["candidates"]
    assert all(item["name"] != "Referred Candidate" for item in staff_candidates)


def test_referral_endpoints_require_staff(client):
    assert client.get("/api/referrals").status_code == 401
    assert client.post("/api/referrals", json={"label": "x"}).status_code == 401

    candidate, csrf, _ = _sign_in("Aya Khan")
    assert candidate.get("/api/referrals").status_code == 403
    assert (
        candidate.post(
            "/api/referrals", json={"label": "x"}, headers={"X-CSRF-Token": csrf}
        ).status_code
        == 403
    )
