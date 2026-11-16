from sqlalchemy import select

from app.database import SessionLocal
from app.models import Membership, User


def test_candidate_cannot_be_managed_as_staff(sign_in):
    supervisor, csrf, _ = sign_in("Noor Ahmed")
    candidate = supervisor.get("/api/staff/workspace").json()["candidates"][0]
    for payload in ({"role": "supervisor"}, {"active": False}, {"team": "Test"}):
        response = supervisor.patch(
            f"/api/staff/members/{candidate['id']}",
            json=payload,
            headers={"X-CSRF-Token": csrf},
        )
        assert response.status_code == 403
    with SessionLocal() as db:
        assert db.get(User, candidate["id"]).role == "candidate"


def test_last_membership_deactivation_disables_identity(sign_in):
    supervisor, csrf, _ = sign_in("Noor Ahmed")
    _, _, employee = sign_in("Sam Ali")
    response = supervisor.patch(
        f"/api/staff/members/{employee['user']['id']}",
        json={"active": False},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    with SessionLocal() as db:
        assert not db.get(User, employee["user"]["id"]).is_active
        assert not db.scalar(select(Membership).where(
            Membership.user_id == employee["user"]["id"]
        )).active
