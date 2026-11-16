"""workspace and session lookup indexes

Revision ID: a7d2e5c91f04
Revises: c4a9f1b2d7e8
Create Date: 2026-11-13 10:00:00.000000

Additive only: these indexes back the bounded, ordered workspace queries and the
session purge/validation lookups. No table or column changes.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "a7d2e5c91f04"
down_revision: str | None = "c4a9f1b2d7e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEXES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("ix_jobs_agency_created", "jobs", ("agency_id", "created_at")),
    ("ix_applications_agency_updated", "applications", ("agency_id", "updated_at")),
    ("ix_applications_candidate_updated", "applications", ("candidate_id", "updated_at")),
    ("ix_activities_agency_created", "activities", ("agency_id", "created_at")),
    ("ix_auth_sessions_user_revoked", "auth_sessions", ("user_id", "revoked_at")),
    ("ix_auth_sessions_expires", "auth_sessions", ("expires_at",)),
    ("ix_memberships_agency_active", "memberships", ("agency_id", "active")),
    ("ix_candidate_assignments_agency", "candidate_assignments", ("agency_id",)),
    ("ix_referral_links_agency_created", "referral_links", ("agency_id", "created_at")),
    ("ix_referral_links_used_by", "referral_links", ("used_by",)),
)


def upgrade() -> None:
    for name, table, columns in INDEXES:
        op.create_index(name, table, list(columns))


def downgrade() -> None:
    for name, table, _columns in reversed(INDEXES):
        op.drop_index(name, table_name=table)
