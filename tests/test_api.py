from fastapi.testclient import TestClient

from app.main import app


def test_demo_session_lifecycle(sign_in):
    client, csrf, session = sign_in("Aya Khan")
    assert session["user"]["role"] == "candidate"
    assert session["user"]["workspace"] == "candidate"
    assert session["agency"]["name"] == "Northstar Careers"
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
        "/api/candidates/me/onboarding/profile/complete",
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


def test_candidate_onboarding_order_and_documents(sign_in):
    client, csrf, _ = sign_in("Aya Khan")
    early = client.post(
        "/api/candidates/me/onboarding/documents/complete",
        headers={"X-CSRF-Token": csrf},
    )
    assert early.status_code == 409

    updated = client.patch(
        "/api/candidates/me/profile",
        json={
            "headline": "Product designer",
            "location": "Lahore, Pakistan",
            "skills": ["Figma", "Research"],
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert updated.status_code == 200
    completed = client.post(
        "/api/candidates/me/onboarding/profile/complete",
        headers={"X-CSRF-Token": csrf},
    )
    assert completed.status_code == 200
    assert completed.json()["profile"]["completion"] == 40

    prefs = client.patch(
        "/api/candidates/me/preferences",
        json={
            "preferredWorkType": "Remote",
            "preferredLocation": "Remote",
            "salaryExpectation": "$90k",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert prefs.status_code == 200
    assert (
        client.post(
            "/api/candidates/me/onboarding/preferences/complete",
            headers={"X-CSRF-Token": csrf},
        ).json()["profile"]["completion"]
        == 70
    )

    upload = client.post(
        "/api/candidates/me/documents",
        files={"file": ("cv.pdf", b"%PDF-1.4 test", "application/pdf")},
        headers={"X-CSRF-Token": csrf},
    )
    assert upload.status_code == 200, upload.text
    document = upload.json()["documents"][0]
    download = client.get(f"/api/candidates/me/documents/{document['id']}")
    assert download.status_code == 200
    assert download.content == b"%PDF-1.4 test"
    done = client.post(
        "/api/candidates/me/onboarding/documents/complete",
        headers={"X-CSRF-Token": csrf},
    )
    assert done.json()["profile"]["completion"] == 100
    removed = client.delete(
        f"/api/candidates/me/documents/{document['id']}",
        headers={"X-CSRF-Token": csrf},
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
    jobs = client.get("/api/jobs/workspace").json()
    assert all(job["title"] == "Content Designer" for job in jobs["jobs"])

    northstar, _csrf, _ = sign_in("Aya Khan")
    assert all(
        job["title"] != "Content Designer"
        for job in northstar.get("/api/jobs/workspace").json()["jobs"]
    )


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


def test_job_application_shared_workflow(sign_in):
    candidate, csrf, _ = sign_in("Aya Khan")
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
