"""create route_revisions table

Revision ID: a3f1c2d4e5b6
Revises: 855431646849
Create Date: 2026-10-23 08:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a3f1c2d4e5b6"
down_revision: Union[str, Sequence[str], None] = "855431646849"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "route_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("route_id", sa.Uuid(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("author_kind", sa.Text(), nullable=False),
        sa.Column("author_ref", sa.Text(), nullable=True),
        sa.Column(
            "before_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "after_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("application_status", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["route_id"], ["routes.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "route_id",
            "revision_number",
            name="uq_route_revisions_route_id_revision_number",
        ),
    )


def downgrade() -> None:
    op.drop_table("route_revisions")
