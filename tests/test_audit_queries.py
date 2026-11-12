import pytest
from sqlalchemy import event

from app.database import SessionLocal, engine
from app.models import Agency, Membership, User


@pytest.mark.parametrize(
    "name,path",
    [
        ("Sam Ali", "/api/staff/workspace"),
        ("Jules Lee", "/api/platform/workspace"),
    ],
)
def test_workspace_counts_do_not_grow_per_record(sign_in, name, path):
    client, _, session = sign_in(name)

    def count_queries():
        queries = []

        def record(*args):
            queries.append(args[2])

        event.listen(engine, "before_cursor_execute", record)
        try:
            assert client.get(path).status_code == 200
        finally:
            event.remove(engine, "before_cursor_execute", record)
        return len(queries)

    before = count_queries()
    with SessionLocal() as db:
        if session["agency"]:
            password = db.get(User, session["user"]["id"]).password_hash
            for i in range(10):
                user = User(
                    name="Load",
                    email=f"load{i}@example.com",
                    password_hash=password,
                    role="employee",
                )
                db.add(user)
                db.flush()
                db.add(Membership(user_id=user.id, agency_id=session["agency"]["id"]))
        else:
            db.add_all(Agency(name=f"Load {i}", slug=f"load-{i}") for i in range(10))
        db.commit()
    assert count_queries() <= before + 2
