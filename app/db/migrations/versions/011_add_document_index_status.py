"""Add per-index status fields to documents

Revision ID: 011
Revises: 010
Create Date: 2026-01-28
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add embeddings_status and bm25_status columns."""
    status_enum = sa.Enum("pending", "processing", "completed", "failed", name="documentstatus")

    op.add_column(
        "documents",
        sa.Column("embeddings_status", status_enum, nullable=False, server_default="pending"),
    )
    op.add_column(
        "documents", sa.Column("bm25_status", status_enum, nullable=False, server_default="pending")
    )

    # Backfill embeddings_status from existing document status
    op.execute("UPDATE documents SET embeddings_status = status WHERE status IS NOT NULL")

    # For BM25, treat completed docs as pending (reindex needed), otherwise mirror status
    op.execute(
        "UPDATE documents SET bm25_status = CASE WHEN status = 'completed' THEN 'pending' ELSE status END "
        "WHERE status IS NOT NULL"
    )

    op.alter_column("documents", "embeddings_status", server_default=None)
    op.alter_column("documents", "bm25_status", server_default=None)


def downgrade() -> None:
    """Remove embeddings_status and bm25_status columns."""
    op.drop_column("documents", "bm25_status")
    op.drop_column("documents", "embeddings_status")
