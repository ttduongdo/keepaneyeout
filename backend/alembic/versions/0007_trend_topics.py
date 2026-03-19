"""add trend topics table

Revision ID: 0007_trend_topics
Revises: 0006_post_metadata
Create Date: 2026-03-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0007_trend_topics"
down_revision = "0006_post_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trend_topics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("growth_rate", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("trend_topics")
