"""candidate independence, normalized profiles, referral links

Revision ID: c4a9f1b2d7e8
Revises: 83f1a1cd3f41
Create Date: 2026-11-12 09:00:00.000000

Moves candidate profile data into normalized tables, allows candidates without an
agency, adds referral links, and expands onboarding to four steps.

The SQLite path rebuilds ``candidate_profiles`` with ``legacy_alter_table`` so the
child tables keep referencing the table name instead of the renamed copy. Downgrade
removes candidate profiles that have no agency, because the previous schema cannot
represent an independent candidate.
"""

import json
import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c4a9f1b2d7e8"
down_revision: str | None = "83f1a1cd3f41"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _create_normalized_tables() -> None:
    op.create_table(
        "candidate_preferences",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("work_type", sa.String(length=40), nullable=False),
        sa.Column("preferred_location", sa.String(length=160), nullable=False),
        sa.Column("salary_expectation", sa.String(length=80), nullable=False),
        sa.Column("availability", sa.String(length=80), nullable=False),
        sa.Column("willing_to_relocate", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["candidate_profiles.user_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "candidate_experiences",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("company", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("location", sa.String(length=160), nullable=False),
        sa.Column("start_date", sa.String(length=7), nullable=False),
        sa.Column("end_date", sa.String(length=7), nullable=True),
        sa.Column("current", sa.Boolean(), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_id"], ["candidate_profiles.user_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("candidate_experiences", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_candidate_experiences_candidate_id"), ["candidate_id"], unique=False
        )
    op.create_table(
        "candidate_education",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("institution", sa.String(length=160), nullable=False),
        sa.Column("degree", sa.String(length=160), nullable=False),
        sa.Column("field_of_study", sa.String(length=160), nullable=False),
        sa.Column("start_year", sa.Integer(), nullable=False),
        sa.Column("end_year", sa.Integer(), nullable=True),
        sa.Column("grade", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_id"], ["candidate_profiles.user_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("candidate_education", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_candidate_education_candidate_id"), ["candidate_id"], unique=False
        )
    op.create_table(
        "candidate_skills",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_id"], ["candidate_profiles.user_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("candidate_id", "name", name="uq_candidate_skill"),
    )
    with op.batch_alter_table("candidate_skills", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_candidate_skills_candidate_id"), ["candidate_id"], unique=False
        )
    op.create_table(
        "referral_links",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("agency_id", sa.String(length=36), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("token_hint", sa.String(length=12), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("used_by", sa.String(length=36), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agency_id"], ["agencies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["used_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("referral_links", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_referral_links_token_hash"), ["token_hash"], unique=True
        )


def _new_profile_table() -> sa.Table:
    metadata = sa.MetaData()
    sa.Table("agencies", metadata, sa.Column("id", sa.String(length=36), primary_key=True))
    sa.Table("users", metadata, sa.Column("id", sa.String(length=36), primary_key=True))
    return sa.Table(
        "candidate_profiles",
        metadata,
        sa.Column("user_id", sa.String(length=36), primary_key=True),
        sa.Column("agency_id", sa.String(length=36), nullable=True),
        sa.Column("headline", sa.String(length=160), nullable=False),
        sa.Column("summary", sa.String(length=1000), nullable=False),
        sa.Column("phone", sa.String(length=40), nullable=False),
        sa.Column("location", sa.String(length=160), nullable=False),
        sa.Column("linkedin_url", sa.String(length=255), nullable=False),
        sa.Column("portfolio_url", sa.String(length=255), nullable=False),
        sa.Column("current_title", sa.String(length=120), nullable=False),
        sa.Column("experience_level", sa.String(length=40), nullable=False),
        sa.Column("stage", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agency_id"], ["agencies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )


def _legacy_profile_table() -> sa.Table:
    metadata = sa.MetaData()
    sa.Table("agencies", metadata, sa.Column("id", sa.String(length=36), primary_key=True))
    sa.Table("users", metadata, sa.Column("id", sa.String(length=36), primary_key=True))
    return sa.Table(
        "candidate_profiles",
        metadata,
        sa.Column("user_id", sa.String(length=36), primary_key=True),
        sa.Column("agency_id", sa.String(length=36), nullable=False),
        sa.Column("headline", sa.String(length=160), nullable=False),
        sa.Column("location", sa.String(length=160), nullable=False),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column("preferred_work_type", sa.String(length=40), nullable=False),
        sa.Column("preferred_location", sa.String(length=160), nullable=False),
        sa.Column("salary_expectation", sa.String(length=80), nullable=False),
        sa.Column("stage", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agency_id"], ["agencies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )


def _skill_names(value) -> list[str]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return []
    if not isinstance(value, list):
        return []
    return [name.strip() for name in value if isinstance(name, str) and name.strip()]


def _backfill_normalized() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT user_id, agency_id, headline, location, skills, preferred_work_type, "
            "preferred_location, salary_expectation, stage, created_at, updated_at "
            "FROM candidate_profiles"
        )
    ).mappings().all()

    for row in rows:
        bind.execute(
            sa.text(
                "INSERT INTO candidate_preferences "
                "(user_id, work_type, preferred_location, salary_expectation, availability, "
                "willing_to_relocate, updated_at) VALUES "
                "(:user_id, :work_type, :preferred_location, :salary_expectation, '', 0, :now)"
            ),
            {
                "user_id": row["user_id"],
                "work_type": row["preferred_work_type"] or "",
                "preferred_location": row["preferred_location"] or "",
                "salary_expectation": row["salary_expectation"] or "",
                "now": row["updated_at"],
            },
        )
        for name in dict.fromkeys(_skill_names(row["skills"])):
            bind.execute(
                sa.text(
                    "INSERT INTO candidate_skills (id, candidate_id, name, created_at) "
                    "VALUES (:id, :candidate_id, :name, :created_at)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "candidate_id": row["user_id"],
                    "name": name,
                    "created_at": row["created_at"],
                },
            )


def _rebuild_profiles_for_upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT user_id, agency_id, headline, location, stage, created_at, updated_at "
            "FROM candidate_profiles"
        )
    ).mappings().all()

    # Keep child foreign keys pointing at the table name while the parent is rebuilt.
    bind.exec_driver_sql("PRAGMA legacy_alter_table=ON")
    bind.exec_driver_sql("ALTER TABLE candidate_profiles RENAME TO candidate_profiles_old")
    _new_profile_table().create(bind)
    if rows:
        bind.execute(
            sa.text(
                "INSERT INTO candidate_profiles "
                "(user_id, agency_id, headline, summary, phone, location, linkedin_url, "
                "portfolio_url, current_title, experience_level, stage, created_at, updated_at) "
                "VALUES (:user_id, :agency_id, :headline, '', '', :location, '', '', '', '', "
                ":stage, :created_at, :updated_at)"
            ),
            [dict(row) for row in rows],
        )
    bind.exec_driver_sql("DROP TABLE candidate_profiles_old")
    bind.exec_driver_sql("PRAGMA legacy_alter_table=OFF")


def _alter_profiles_for_upgrade() -> None:
    for name, column in (
        ("phone", sa.Column("phone", sa.String(length=40), nullable=False, server_default="")),
        (
            "summary",
            sa.Column("summary", sa.String(length=1000), nullable=False, server_default=""),
        ),
        (
            "linkedin_url",
            sa.Column("linkedin_url", sa.String(length=255), nullable=False, server_default=""),
        ),
        (
            "portfolio_url",
            sa.Column("portfolio_url", sa.String(length=255), nullable=False, server_default=""),
        ),
        (
            "current_title",
            sa.Column("current_title", sa.String(length=120), nullable=False, server_default=""),
        ),
        (
            "experience_level",
            sa.Column("experience_level", sa.String(length=40), nullable=False, server_default=""),
        ),
    ):
        op.add_column("candidate_profiles", column)
        op.alter_column("candidate_profiles", name, server_default=None)
    op.alter_column(
        "candidate_profiles", "agency_id", existing_type=sa.String(length=36), nullable=True
    )
    op.drop_constraint(
        "candidate_profiles_agency_id_fkey", "candidate_profiles", type_="foreignkey"
    )
    op.create_foreign_key(
        "candidate_profiles_agency_id_fkey",
        "candidate_profiles",
        "agencies",
        ["agency_id"],
        ["id"],
        ondelete="SET NULL",
    )
    for name in ("skills", "preferred_work_type", "preferred_location", "salary_expectation"):
        op.drop_column("candidate_profiles", name)


def _migrate_onboarding_keys() -> None:
    bind = op.get_bind()
    steps = bind.execute(
        sa.text(
            "SELECT id, candidate_id, key, position, status, completed_at FROM onboarding_steps"
        )
    ).mappings().all()
    grouped: dict[str, list] = {}
    for step in steps:
        grouped.setdefault(step["candidate_id"], []).append(step)

    key_map = {"profile": "personal", "preferences": "professional", "documents": "documents"}
    for candidate_id, candidate_steps in grouped.items():
        by_key = {key_map.get(step["key"], step["key"]): step for step in candidate_steps}
        documents = by_key.get("documents")
        documents_status = documents["status"] if documents else "upcoming"
        academic_status = "upcoming"
        if documents_status == "next":
            academic_status = "next"
            documents_status = "upcoming"
        layout = (
            ("personal", 0, by_key.get("personal")),
            ("professional", 1, by_key.get("professional")),
            ("academic", 2, None),
            ("documents", 3, documents),
        )
        bind.execute(
            sa.text("DELETE FROM onboarding_steps WHERE candidate_id = :candidate_id"),
            {"candidate_id": candidate_id},
        )
        for key, position, source in layout:
            if key == "academic":
                status, completed_at = academic_status, None
            elif source is None:
                status, completed_at = "upcoming", None
            else:
                status = documents_status if key == "documents" else source["status"]
                completed_at = source["completed_at"]
            bind.execute(
                sa.text(
                    "INSERT INTO onboarding_steps "
                    "(id, candidate_id, key, position, status, completed_at) "
                    "VALUES (:id, :candidate_id, :key, :position, :status, :completed_at)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "candidate_id": candidate_id,
                    "key": key,
                    "position": position,
                    "status": status,
                    "completed_at": completed_at,
                },
            )


def _backfill_flat_columns() -> None:
    """Copy normalized rows back into the flat columns the old schema expects."""
    bind = op.get_bind()
    profiles = bind.execute(
        sa.text("SELECT user_id FROM candidate_profiles")
    ).mappings().all()
    for profile in profiles:
        skills = [
            row[0]
            for row in bind.execute(
                sa.text(
                    "SELECT name FROM candidate_skills WHERE candidate_id = :candidate_id "
                    "ORDER BY name"
                ),
                {"candidate_id": profile["user_id"]},
            )
        ]
        preference = bind.execute(
            sa.text(
                "SELECT work_type, preferred_location, salary_expectation "
                "FROM candidate_preferences WHERE user_id = :user_id"
            ),
            {"user_id": profile["user_id"]},
        ).mappings().first()
        bind.execute(
            sa.text(
                "UPDATE candidate_profiles SET skills = :skills, "
                "preferred_work_type = :work_type, preferred_location = :preferred_location, "
                "salary_expectation = :salary_expectation WHERE user_id = :user_id"
                if bind.dialect.name == "sqlite"
                else "UPDATE candidate_profiles SET skills = CAST(:skills AS JSON), "
                "preferred_work_type = :work_type, preferred_location = :preferred_location, "
                "salary_expectation = :salary_expectation WHERE user_id = :user_id"
            ),
            {
                "skills": json.dumps(skills),
                "work_type": preference["work_type"] if preference else "",
                "preferred_location": preference["preferred_location"] if preference else "",
                "salary_expectation": preference["salary_expectation"] if preference else "",
                "user_id": profile["user_id"],
            },
        )


def _restore_flat_columns() -> None:
    bind = op.get_bind()
    sqlite = bind.dialect.name == "sqlite"
    if sqlite:
        for statement in (
            "ALTER TABLE candidate_profiles ADD COLUMN skills JSON NOT NULL DEFAULT '[]'",
            "ALTER TABLE candidate_profiles ADD COLUMN preferred_work_type VARCHAR(40) "
            "NOT NULL DEFAULT ''",
            "ALTER TABLE candidate_profiles ADD COLUMN preferred_location VARCHAR(160) "
            "NOT NULL DEFAULT ''",
            "ALTER TABLE candidate_profiles ADD COLUMN salary_expectation VARCHAR(80) "
            "NOT NULL DEFAULT ''",
        ):
            op.execute(statement)
    else:
        for name, column in (
            ("skills", sa.Column("skills", sa.JSON(), nullable=False, server_default="[]")),
            (
                "preferred_work_type",
                sa.Column(
                    "preferred_work_type", sa.String(length=40), nullable=False, server_default=""
                ),
            ),
            (
                "preferred_location",
                sa.Column(
                    "preferred_location", sa.String(length=160), nullable=False, server_default=""
                ),
            ),
            (
                "salary_expectation",
                sa.Column(
                    "salary_expectation", sa.String(length=80), nullable=False, server_default=""
                ),
            ),
        ):
            op.add_column("candidate_profiles", column)
            op.alter_column("candidate_profiles", name, server_default=None)


def _rebuild_profiles_for_downgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT user_id, agency_id, headline, location, skills, preferred_work_type, "
            "preferred_location, salary_expectation, stage, created_at, updated_at "
            "FROM candidate_profiles"
        )
    ).mappings().all()
    sqlite = bind.dialect.name == "sqlite"

    if sqlite:
        bind.exec_driver_sql("PRAGMA legacy_alter_table=ON")
        bind.exec_driver_sql("ALTER TABLE candidate_profiles RENAME TO candidate_profiles_new")
        _legacy_profile_table().create(bind)
        if rows:
            bind.execute(
                sa.text(
                    "INSERT INTO candidate_profiles "
                    "(user_id, agency_id, headline, location, skills, preferred_work_type, "
                    "preferred_location, salary_expectation, stage, created_at, updated_at) "
                    "VALUES (:user_id, :agency_id, :headline, :location, :skills, "
                    ":preferred_work_type, :preferred_location, :salary_expectation, :stage, "
                    ":created_at, :updated_at)"
                ),
                [dict(row) for row in rows],
            )
        bind.exec_driver_sql("DROP TABLE candidate_profiles_new")
        bind.exec_driver_sql("PRAGMA legacy_alter_table=OFF")
        return

    op.drop_constraint(
        "candidate_profiles_agency_id_fkey", "candidate_profiles", type_="foreignkey"
    )
    op.create_foreign_key(
        "candidate_profiles_agency_id_fkey",
        "candidate_profiles",
        "agencies",
        ["agency_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.alter_column(
        "candidate_profiles", "agency_id", existing_type=sa.String(length=36), nullable=False
    )
    for name in (
        "phone",
        "summary",
        "linkedin_url",
        "portfolio_url",
        "current_title",
        "experience_level",
    ):
        op.drop_column("candidate_profiles", name)


def _revert_onboarding_keys() -> None:
    bind = op.get_bind()
    academic_next = bind.execute(
        sa.text(
            "SELECT candidate_id FROM onboarding_steps "
            "WHERE key = 'academic' AND status = 'next'"
        )
    ).scalars().all()
    for candidate_id in academic_next:
        bind.execute(
            sa.text(
                "UPDATE onboarding_steps SET status = 'next' "
                "WHERE candidate_id = :candidate_id AND key = 'documents'"
            ),
            {"candidate_id": candidate_id},
        )
    bind.execute(sa.text("DELETE FROM onboarding_steps WHERE key = 'academic'"))
    bind.execute(
        sa.text("UPDATE onboarding_steps SET key = 'profile', position = 0 WHERE key = 'personal'")
    )
    bind.execute(
        sa.text(
            "UPDATE onboarding_steps SET key = 'preferences', position = 1 "
            "WHERE key = 'professional'"
        )
    )
    bind.execute(sa.text("UPDATE onboarding_steps SET position = 2 WHERE key = 'documents'"))


def upgrade() -> None:
    _create_normalized_tables()
    _backfill_normalized()
    if op.get_bind().dialect.name == "sqlite":
        _rebuild_profiles_for_upgrade()
    else:
        _alter_profiles_for_upgrade()
    _migrate_onboarding_keys()


def downgrade() -> None:
    bind = op.get_bind()

    # The previous schema cannot store a candidate without an agency.
    bind.execute(sa.text("DELETE FROM candidate_profiles WHERE agency_id IS NULL"))

    _restore_flat_columns()
    _backfill_flat_columns()
    _rebuild_profiles_for_downgrade()
    _revert_onboarding_keys()

    op.drop_table("referral_links")
    with op.batch_alter_table("candidate_skills", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_candidate_skills_candidate_id"))
    op.drop_table("candidate_skills")
    with op.batch_alter_table("candidate_education", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_candidate_education_candidate_id"))
    op.drop_table("candidate_education")
    with op.batch_alter_table("candidate_experiences", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_candidate_experiences_candidate_id"))
    op.drop_table("candidate_experiences")
    op.drop_table("candidate_preferences")
