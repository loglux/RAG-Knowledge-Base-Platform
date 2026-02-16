"""Add upsert_batch_size to knowledge_bases

Revision ID: 004
Revises: 003
Create Date: 2026-01-26
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add upsert_batch_size column to knowledge_bases."""
    op.add_column(
        "knowledge_bases",
        sa.Column("upsert_batch_size", sa.Integer(), nullable=False, server_default="256"),
    )


def downgrade() -> None:
    """Remove upsert_batch_size column."""
    op.drop_column("knowledge_bases", "upsert_batch_size")
