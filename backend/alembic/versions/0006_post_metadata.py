"""add post metadata columns to documents

Revision ID: 0006_post_metadata
Revises: 0005_trends
Create Date: 2026-03-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = "0006_post_metadata"
down_revision = "0005_trends"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column(
        "documents",
        sa.Column("authors", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'::text[]")),
    )
    op.add_column("documents", sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.add_column("documents", sa.Column("thumbnail_url", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("embedding", Vector(3072), nullable=True))
    op.add_column("documents", sa.Column("topic_cluster", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "topic_cluster")
    op.drop_column("documents", "embedding")
    op.drop_column("documents", "thumbnail_url")
    op.drop_column("documents", "ingested_at")
    op.drop_column("documents", "authors")
    op.drop_column("documents", "summary")
