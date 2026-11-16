from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_demo_session_lifecycle(sign_in):
    client, csrf, session = sign_in("Aya Khan")
    assert session["user"]["role"] == "candidate"
    assert session["user"]["workspace"] == "candidate"
    # Independent candidates are not attached to an agency.
    assert session["agency"] is None
    assert session["user"]["agencies"] == []
    current = client.get("/api/auth/session")
    assert current.status_code == 200
    assert current.json()["user"]["name"] == "Aya Khan"
    logout = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
    assert logout.status_code == 204
    assert client.get("/api/auth/session").json() is None


def test_session_requires_cookie(client):
    assert client.get("/api/auth/session").json() is None
    assert client.get("/api/candidates/me").status_code == 401
    assert client.get("/api/staff/workspace").status_code == 401
    assert client.get("/api/platform/workspace").status_code == 401


def test_csrf_is_required_for_mutations(sign_in):
    client, _csrf, _ = sign_in("Sam Ali")
    assert client.patch("/api/jobs/missing", json={"status": "closed"}).status_code == 403
    bypass = client.patch(
        "/api/jobs/missing",
        json={"status": "closed"},
        headers={"X-CSRF-Token": "wrong"},
    )
    assert bypass.status_code == 403


def test_register_login_and_duplicate_email(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "New Candidate",
            "email": "new.candidate@example.com",
            "password": "Password123!",
        },
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["user"]["role"] == "candidate"
    assert client.get("/api/candidates/me").json()["profile"]["name"] == "New Candidate"

    duplicate = client.post(
        "/api/auth/register",
        json={
            "name": "Someone Else",
            "email": "new.candidate@example.com",
            "password": "Password123!",
        },
        headers={"Origin": "http://localhost:3000"},
    )
    assert duplicate.status_code == 409

    login = client.post(
        "/api/auth/login",
        json={"email": "new.candidate@example.com", "password": "Password123!"},
        headers={"Origin": "http://localhost:3000"},
    )
    assert login.status_code == 200
    wrong = client.post(
        "/api/auth/login",
        json={"email": "new.candidate@example.com", "password": "nope"},
        headers={"Origin": "http://localhost:3000"},
    )
    assert wrong.status_code == 401


def test_new_candidate_must_complete_profile_fields_first(client):
    client.post(
        "/api/auth/register",
        json={
            "name": "Empty Profile",
            "email": "empty.profile@example.com",
            "password": "Password123!",
        },
        headers={"Origin": "http://localhost:3000"},
    )
    csrf = client.cookies.get("jf_csrf")
    response = client.post(
        "/api/candidates/me/onboarding/personal/complete",
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 409


def test_disallowed_origin_is_rejected(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "aya@demo.example.com", "password": "Demo1234!"},
        headers={"Origin": "https://evil.example.com"},
    )
    assert response.status_code == 403


def test_docs_testing_origin_and_csrf_interceptor(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "docs_testing_enabled", True)
    allowed = client.post(
        "/api/auth/login",
        json={"email": "aya@demo.example.com", "password": "Demo1234!"},
        headers={"Origin": "http://testserver"},
    )
    assert allowed.status_code == 200

    docs = client.get("/docs")
    assert docs.status_code == 200
    assert "X-CSRF-Token" in docs.text

    monkeypatch.setattr(settings, "docs_testing_enabled", False)
    denied = client.post(
        "/api/auth/login",
        json={"email": "aya@demo.example.com", "password": "Demo1234!"},
        headers={"Origin": "http://testserver"},
    )
    assert denied.status_code == 403


def test_candidate_onboarding_order_and_documents(sign_in, valid_pdf):
    client, csrf, _ = sign_in("Aya Khan")
    headers = {"X-CSRF-Token": csrf}
    early = client.post("/api/candidates/me/onboarding/documents/complete", headers=headers)
    assert early.status_code == 409

    # The order is enforced while saving, not only while completing.
    out_of_order = client.put(
        "/api/candidates/me/onboarding/professional",
        json={
            "currentTitle": "Product designer",
            "experienceLevel": "Junior",
            "skills": ["Figma"],
            "experiences": [],
            "preferences": {"workType": "Remote"},
        },
        headers=headers,
    )
    assert out_of_order.status_code == 409

    personal = client.put(
        "/api/candidates/me/onboarding/personal",
        json={
            "phone": "+92 300 1234567",
            "location": "Lahore, Pakistan",
            "headline": "Product designer",
            "summary": "Designer moving into product.",
        },
        headers=headers,
    )
    assert personal.status_code == 200, personal.text
    completed = client.post("/api/candidates/me/onboarding/personal/complete", headers=headers)
    assert completed.status_code == 200
    assert completed.json()["profile"]["completion"] == 20

    professional = client.put(
        "/api/candidates/me/onboarding/professional",
        json={
            "currentTitle": "Product designer",
            "experienceLevel": "Junior",
            "skills": ["Figma", "Research", "figma"],
            "experiences": [
                {
                    "company": "Studio One",
                    "title": "Designer",
                    "location": "Lahore",
                    "startDate": "2022-01",
                    "current": True,
                    "description": "Worked on discovery.",
                }
            ],
            "preferences": {
                "workType": "Remote",
                "preferredLocation": "Remote",
                "salaryExpectation": "$40k",
                "availability": "1 month",
                "willingToRelocate": False,
            },
        },
        headers=headers,
    )
    assert professional.status_code == 200, professional.text
    assert professional.json()["skills"] == ["Figma", "Research"]
    advanced = client.post("/api/candidates/me/onboarding/professional/complete", headers=headers)
    assert advanced.json()["profile"]["completion"] == 50

    academic = client.put(
        "/api/candidates/me/onboarding/academic",
        json={
            "education": [
                {
                    "institution": "Punjab University",
                    "degree": "BSc",
                    "fieldOfStudy": "Computer Science",
                    "startYear": 2018,
                    "endYear": 2022,
                    "grade": "3.6 GPA",
                }
            ]
        },
        headers=headers,
    )
    assert academic.status_code == 200, academic.text
    assert (
        client.post("/api/candidates/me/onboarding/academic/complete", headers=headers).json()[
            "profile"
        ]["completion"]
        == 75
    )

    upload = client.post(
        "/api/candidates/me/documents",
        files={"file": ("cv.pdf", valid_pdf, "application/pdf")},
        headers=headers,
    )
    assert upload.status_code == 200, upload.text
    document = upload.json()["documents"][0]
    download = client.get(f"/api/candidates/me/documents/{document['id']}")
    assert download.status_code == 200
    assert download.content == valid_pdf
    done = client.post("/api/candidates/me/onboarding/documents/complete", headers=headers)
    assert done.json()["profile"]["completion"] == 100
    assert done.json()["onboardingComplete"] is True

    # Saved progress survives a logout/login cycle, including normalized data.
    assert client.post("/api/auth/logout", headers=headers).status_code == 204
    login = client.post(
        "/api/auth/login",
        json={"email": "aya@demo.example.com", "password": "Demo1234!"},
        headers={"Origin": "http://localhost:3000"},
    )
    assert login.status_code == 200
    resumed = client.get("/api/candidates/me").json()
    assert resumed["profile"]["completion"] == 100
    assert resumed["experiences"][0]["company"] == "Studio One"
    assert resumed["education"][0]["institution"] == "Punjab University"
    assert resumed["preferences"]["preferredLocation"] == "Remote"

    removed = client.delete(
        f"/api/candidates/me/documents/{document['id']}",
        headers={"X-CSRF-Token": client.cookies.get("jf_csrf")},
    )
    assert removed.status_code == 200
    assert removed.json()["documents"] == []


def test_candidate_cannot_read_another_agency(sign_in):
    client = TestClient(app)
    login = client.post(
        "/api/auth/login",
        json={"email": "mia@harbor.example.com", "password": "Demo1234!"},
        headers={"Origin": "http://localhost:3000"},
    )
    assert login.status_code == 200
    workspace = client.get("/api/candidates/me").json()
    assert workspace["profile"]["name"] == "Mia Chen"
    assert workspace["referral"]["agencyName"] == "Harbor Talent"
    jobs = client.get("/api/jobs/workspace").json()
    assert {job["title"] for job in jobs["jobs"]} == {"Content Designer"}

    # Independent candidates see every open role across active agencies.
    independent, _csrf, _ = sign_in("Aya Khan")
    independent_jobs = independent.get("/api/jobs/workspace").json()["jobs"]
    assert "Content Designer" in {job["title"] for job in independent_jobs}
    assert len(independent_jobs) == 5


def test_employee_read_only_and_supervisor_management(sign_in):
    employee, ecsrf, _ = sign_in("Sam Ali")
    workspace = employee.get("/api/staff/workspace")
    assert workspace.status_code == 200
    candidate_id = workspace.json()["candidates"][0]["id"]
    member_id = workspace.json()["teamMembers"][0]["id"]
    denied = employee.post(
        f"/api/staff/candidates/{candidate_id}/assignment",
        json={"memberId": member_id},
        headers={"X-CSRF-Token": ecsrf},
    )
    assert denied.status_code == 403
    assert (
        employee.post(
            "/api/staff/members",
            json={
                "name": "Denied",
                "email": "denied@northstar.example.com",
                "role": "employee",
                "team": "Candidate success",
            },
            headers={"X-CSRF-Token": ecsrf},
        ).status_code
        == 403
    )

    supervisor, csrf, _ = sign_in("Noor Ahmed")
    created = supervisor.post(
        "/api/staff/members",
        json={
            "name": "Jordan Kim",
            "email": "jordan@northstar.example.com",
            "role": "employee",
            "team": "Candidate success",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 200
    temporary = created.json()["temporaryPassword"]
    new_member = next(
        member
        for member in created.json()["workspace"]["teamMembers"]
        if member["name"] == "Jordan Kim"
    )
    assert new_member["active"] is True

    new_client = TestClient(employee.app)
    login = new_client.post(
        "/api/auth/login",
        json={"email": "jordan@northstar.example.com", "password": temporary},
        headers={"Origin": "http://localhost:3000"},
    )
    assert login.status_code == 200

    deactivated = supervisor.patch(
        f"/api/staff/members/{new_member['id']}",
        json={"active": False},
        headers={"X-CSRF-Token": csrf},
    )
    assert deactivated.status_code == 200
    assert new_client.get("/api/staff/workspace").status_code == 401


def test_assignment_and_cross_agency_denial(sign_in):
    supervisor, csrf, _ = sign_in("Noor Ahmed")
    workspace = supervisor.get("/api/staff/workspace").json()
    ava = next(item for item in workspace["candidates"] if item["name"] == "Ava Johnson")
    member = workspace["teamMembers"][0]
    assigned = supervisor.post(
        f"/api/staff/candidates/{ava['id']}/assignment",
        json={"memberId": member["id"]},
        headers={"X-CSRF-Token": csrf},
    )
    assert assigned.status_code == 200
    updated = next(item for item in assigned.json()["candidates"] if item["id"] == ava["id"])
    assert updated["assignedTo"] == member["id"]
    assert updated["status"] == "review"

    harbor = supervisor.get("/api/auth/session").json()["user"]["agencies"][1]["id"]
    switched = supervisor.post(
        "/api/auth/context",
        json={"agencyId": harbor},
        headers={"X-CSRF-Token": csrf},
    )
    assert switched.status_code == 200
    harbor_workspace = supervisor.get("/api/staff/workspace").json()
    assert all(item["name"] != "Aya Khan" for item in harbor_workspace["candidates"])
    cross = supervisor.post(
        f"/api/staff/candidates/{ava['id']}/assignment",
        json={"memberId": member["id"]},
        headers={"X-CSRF-Token": csrf},
    )
    assert cross.status_code == 404


def test_job_application_shared_workflow(sign_in, complete_onboarding):
    candidate, csrf, _ = sign_in("Aya Khan")
    complete_onboarding(candidate, csrf)
    jobs = candidate.get("/api/jobs/workspace").json()
    frontend = next(job for job in jobs["jobs"] if job["title"] == "Frontend Engineer")
    applied = candidate.post(f"/api/jobs/{frontend['id']}/apply", headers={"X-CSRF-Token": csrf})
    assert applied.status_code == 200
    application = next(
        item for item in applied.json()["applications"] if item["jobId"] == frontend["id"]
    )
    assert application["status"] == "submitted"
    duplicate = candidate.post(f"/api/jobs/{frontend['id']}/apply", headers={"X-CSRF-Token": csrf})
    assert duplicate.status_code == 409
    forbidden = candidate.patch(
        f"/api/applications/{application['id']}",
        json={"status": "offer"},
        headers={"X-CSRF-Token": csrf},
    )
    assert forbidden.status_code == 403

    employee, ecsrf, _ = sign_in("Sam Ali")
    updated = employee.patch(
        f"/api/applications/{application['id']}",
        json={"status": "interview"},
        headers={"X-CSRF-Token": ecsrf},
    )
    assert updated.status_code == 200
    seen = candidate.get("/api/jobs/workspace").json()
    assert (
        next(item for item in seen["applications"] if item["id"] == application["id"])["status"]
        == "interview"
    )

    supervisor, scsrf, _ = sign_in("Noor Ahmed")
    created = supervisor.post(
        "/api/jobs",
        json={
            "title": "QA Engineer",
            "company": "Acme",
            "location": "Remote",
            "workType": "Remote",
            "salary": "$80k",
            "tags": ["Testing"],
            "description": "Test the product",
        },
        headers={"X-CSRF-Token": scsrf},
    )
    assert created.status_code == 200
    new_job = next(job for job in created.json()["jobs"] if job["title"] == "QA Engineer")
    closed = supervisor.patch(
        f"/api/jobs/{new_job['id']}",
        json={"status": "closed"},
        headers={"X-CSRF-Token": scsrf},
    )
    assert (
        next(job for job in closed.json()["jobs"] if job["id"] == new_job["id"])["status"]
        == "closed"
    )


def test_platform_isolation(sign_in):
    candidate, _csrf, _ = sign_in("Aya Khan")
    assert candidate.get("/api/platform/workspace").status_code == 403

    platform, csrf, session = sign_in("Jules Lee")
    assert session["agency"] is None
    workspace = platform.get("/api/platform/workspace")
    assert workspace.status_code == 200
    assert workspace.json()["stats"]["agencies"] == 4
    assert platform.get("/api/staff/workspace").status_code == 403
    agency = workspace.json()["agencies"][0]
    updated = platform.patch(
        f"/api/platform/agencies/{agency['id']}",
        json={"status": "suspended"},
        headers={"X-CSRF-Token": csrf},
    )
    assert updated.status_code == 200
    assert (
        next(item for item in updated.json()["agencies"] if item["id"] == agency["id"])["status"]
        == "suspended"
    )


def test_logout_clears_cookies(sign_in):
    client, csrf, _ = sign_in("Aya Khan")
    response = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
    assert response.status_code == 204
    cookies = " ".join(response.headers.get_list("set-cookie"))
    assert "jf_session=" in cookies
    assert "jf_csrf=" in cookies
    assert client.get("/api/auth/session").json() is None


def test_password_change_revokes_sessions(sign_in):
    client, csrf, _ = sign_in("Aya Khan")
    wrong = client.post(
        "/api/auth/password",
        json={"currentPassword": "nope", "newPassword": "NewPassword123!"},
        headers={"X-CSRF-Token": csrf},
    )
    assert wrong.status_code == 401

    changed = client.post(
        "/api/auth/password",
        json={"currentPassword": "Demo1234!", "newPassword": "NewPassword123!"},
        headers={"X-CSRF-Token": csrf},
    )
    assert changed.status_code == 204
    assert client.get("/api/auth/session").json() is None

    stale = client.post(
        "/api/auth/login",
        json={"email": "aya@demo.example.com", "password": "Demo1234!"},
        headers={"Origin": "http://localhost:3000"},
    )
    assert stale.status_code == 401
    fresh = client.post(
        "/api/auth/login",
        json={"email": "aya@demo.example.com", "password": "NewPassword123!"},
        headers={"Origin": "http://localhost:3000"},
    )
    assert fresh.status_code == 200


def test_stage_updates_are_supervisor_only(sign_in):
    employee, ecsrf, _ = sign_in("Sam Ali")
    workspace = employee.get("/api/staff/workspace").json()
    candidate_id = workspace["candidates"][0]["id"]
    denied = employee.patch(
        f"/api/staff/candidates/{candidate_id}/stage",
        json={"stage": "interview"},
        headers={"X-CSRF-Token": ecsrf},
    )
    assert denied.status_code == 403

    supervisor, csrf, _ = sign_in("Noor Ahmed")
    moved = supervisor.patch(
        f"/api/staff/candidates/{candidate_id}/stage",
        json={"stage": "interview"},
        headers={"X-CSRF-Token": csrf},
    )
    assert moved.status_code == 200
    assert (
        next(item for item in moved.json()["candidates"] if item["id"] == candidate_id)["status"]
        == "interview"
    )


def test_cross_agency_member_mutation_is_denied(sign_in):
    supervisor, csrf, _ = sign_in("Noor Ahmed")
    workspace = supervisor.get("/api/staff/workspace").json()
    northstar_member = workspace["teamMembers"][0]

    harbor = supervisor.get("/api/auth/session").json()["user"]["agencies"][1]["id"]
    supervisor.post("/api/auth/context", json={"agencyId": harbor}, headers={"X-CSRF-Token": csrf})
    denied = supervisor.patch(
        f"/api/staff/members/{northstar_member['id']}",
        json={"active": False},
        headers={"X-CSRF-Token": csrf},
    )
    assert denied.status_code == 404


def test_document_signature_is_validated(sign_in):
    client, csrf, _ = sign_in("Aya Khan")
    spoofed = client.post(
        "/api/candidates/me/documents",
        files={"file": ("cv.pdf", b"not a real pdf", "application/pdf")},
        headers={"X-CSRF-Token": csrf},
    )
    assert spoofed.status_code == 409
    assert client.get("/api/candidates/me").json()["documents"] == []
