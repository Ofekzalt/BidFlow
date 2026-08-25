"""auctions table

Revision ID: 0001
Revises:
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "auctions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("seller_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("starting_price_cents", sa.Integer(), nullable=False),
        sa.Column("current_price_cents", sa.Integer(), nullable=False),
        sa.Column("current_winner_id", sa.UUID(), nullable=True),
        sa.Column("final_amount_cents", sa.Integer(), nullable=True),
        sa.Column("winner_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("auctions")
