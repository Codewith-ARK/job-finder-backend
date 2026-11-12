from pathlib import Path

from alembic.config import Config
from sqlalchemy import inspect, text

from alembic import command
from app.database import Base, engine

ROOT = Path(__file__).resolve().parents[1]


def _index_names() -> set[str]:
    # SQLite's Inspector can return a stale index list after a drop/upgrade cycle
    # in the same engine pool; sqlite_master is the authoritative catalog.
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT name FROM sqlite_master WHERE type = 'index'")
        ).scalars()
        return set(rows)


def test_migrations_create_and_drop_schema():
    Base.metadata.drop_all(bind=engine)
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))

    command.upgrade(config, "head")

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert {
        "agencies",
        "applications",
        "auth_sessions",
        "candidate_education",
        "candidate_experiences",
        "candidate_preferences",
        "candidate_profiles",
        "candidate_skills",
        "jobs",
        "memberships",
        "referral_links",
        "users",
    } <= tables

    indexes = _index_names()
    assert {
        "ix_jobs_agency_created",
        "ix_applications_agency_updated",
        "ix_applications_candidate_updated",
        "ix_activities_agency_created",
        "ix_auth_sessions_user_revoked",
        "ix_auth_sessions_expires",
        "ix_memberships_agency_active",
        "ix_candidate_assignments_agency",
        "ix_referral_links_agency_created",
        "ix_referral_links_used_by",
    } <= indexes

    command.downgrade(config, "base")
    assert inspect(engine).get_table_names() == ["alembic_version"]
    assert not [name for name in _index_names() if name.startswith("ix_")]
