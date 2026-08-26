"""outbox_events table and open-auction claim index

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("event_version", sa.String(length=16), nullable=False),
        sa.Column("aggregate_id", sa.UUID(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_auctions_open_end_time",
        "auctions",
        ["end_time"],
        postgresql_where=sa.text("status = 'OPEN'"),
    )


def downgrade() -> None:
    op.drop_index("ix_auctions_open_end_time", table_name="auctions")
    op.drop_table("outbox_events")
