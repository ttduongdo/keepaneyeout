"""digests and subscriptions

Revision ID: 0003_digests_subscriptions
Revises: 0002_topics
Create Date: 2026-02-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003_digests_subscriptions"
down_revision: Union[str, None] = "0002_topics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "digests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column("stats", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("date", name="uq_digests_date"),
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("topic_ids", postgresql.ARRAY(sa.Uuid()), nullable=False, server_default=sa.text("ARRAY[]::uuid[]")),
        sa.Column("frequency", sa.Text(), nullable=False, server_default=sa.text("'daily'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("unsubscribe_token", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("unsubscribe_token", name="uq_subscriptions_unsubscribe_token"),
    )

    op.create_index("ix_subscriptions_email", "subscriptions", ["email"])
    op.create_index("ix_subscriptions_is_active", "subscriptions", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_subscriptions_is_active", table_name="subscriptions")
    op.drop_index("ix_subscriptions_email", table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_table("digests")
