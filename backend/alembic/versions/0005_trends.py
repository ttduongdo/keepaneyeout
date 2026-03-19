"""add trends table

Revision ID: 0005_trends
Revises: 0004_auth_boards
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0005_trends"
down_revision = "0004_auth_boards"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trends",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False, unique=True),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column("stats", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("trends")
