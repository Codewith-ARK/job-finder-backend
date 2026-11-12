def test_referred_application_respects_agency(sign_in):
    candidate, csrf, _ = sign_in("Aya Khan")
    jobs = candidate.get("/api/jobs/workspace").json()["jobs"]
    foreign = next(j for j in jobs if j["agencyName"] == "Harbor Talent")
    from fastapi.testclient import TestClient

    from app.main import app
    from app.seed import DEMO_REFERRAL_TOKENS

    with TestClient(app) as referred:
        result = referred.post("/api/auth/register", json={
            "name": "Audit", "email": "scope@example.com", "password": "Password123!",
            "referralToken": DEMO_REFERRAL_TOKENS["active"],
        }, headers={"Origin": "http://localhost:3000"})
        assert result.status_code == 200
        response = referred.post(f"/api/jobs/{foreign['id']}/apply", headers={
            "X-CSRF-Token": referred.cookies.get("jf_csrf"),
        })
        assert response.status_code == 404
        assert referred.get("/api/jobs/workspace").json()["applications"] == []


def test_independent_application_preserves_workspace_scope(sign_in):
    candidate, csrf, _ = sign_in("Aya Khan")
    before = candidate.get("/api/jobs/workspace").json()["jobs"]
    job = next(j for j in before if j["title"] == "Frontend Engineer")
    response = candidate.post(f"/api/jobs/{job['id']}/apply", headers={"X-CSRF-Token": csrf})
    assert response.status_code == 200
    assert {j["id"] for j in response.json()["jobs"]} == {j["id"] for j in before}


