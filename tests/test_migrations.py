from pathlib import Path

from alembic.config import Config
from sqlalchemy import inspect

from alembic import command
from app.database import Base, engine

ROOT = Path(__file__).resolve().parents[1]


def test_migrations_create_and_drop_schema():
    Base.metadata.drop_all(bind=engine)
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))

    command.upgrade(config, "head")

    tables = set(inspect(engine).get_table_names())
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

    command.downgrade(config, "base")
    assert inspect(engine).get_table_names() == ["alembic_version"]
