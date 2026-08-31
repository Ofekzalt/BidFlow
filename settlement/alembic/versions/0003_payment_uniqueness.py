"""payment uniqueness and default payment method

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_payment_methods_stripe_payment_method_id",
        "payment_methods",
        ["stripe_payment_method_id"],
    )
    op.create_index(
        "uq_payment_methods_one_default_per_user",
        "payment_methods",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )
    op.create_index(
        "uq_payments_stripe_payment_intent_id",
        "payments",
        ["stripe_payment_intent_id"],
        unique=True,
        postgresql_where=sa.text("stripe_payment_intent_id IS NOT NULL"),
    )
    op.create_index(
        "uq_outbox_one_payment_result_per_auction",
        "outbox_events",
        ["aggregate_id"],
        unique=True,
        postgresql_where=sa.text("event_type IN ('PaymentSucceeded', 'PaymentFailed')"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_outbox_one_payment_result_per_auction", table_name="outbox_events"
    )
    op.drop_index("uq_payments_stripe_payment_intent_id", table_name="payments")
    op.drop_index(
        "uq_payment_methods_one_default_per_user", table_name="payment_methods"
    )
    op.drop_constraint(
        "uq_payment_methods_stripe_payment_method_id",
        "payment_methods",
        type_="unique",
    )
