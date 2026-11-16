"""store document Blob pathnames instead of local filesystem paths

Revision ID: d5b7c9e1f2a3
Revises: a7d2e5c91f04
"""

from collections.abc import Sequence

from alembic import op

revision: str = "d5b7c9e1f2a3"
down_revision: str | None = "a7d2e5c91f04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("documents", "storage_path", new_column_name="blob_pathname")


def downgrade() -> None:
    op.alter_column("documents", "blob_pathname", new_column_name="storage_path")
