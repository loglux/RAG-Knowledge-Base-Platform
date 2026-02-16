"""Add KB defaults to app_settings

Revision ID: 009
Revises: 008
Create Date: 2026-01-28
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add KB defaults columns."""
    op.add_column("app_settings", sa.Column("kb_chunk_size", sa.Integer(), nullable=True))
    op.add_column("app_settings", sa.Column("kb_chunk_overlap", sa.Integer(), nullable=True))
    op.add_column("app_settings", sa.Column("kb_upsert_batch_size", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Remove KB defaults columns."""
    op.drop_column("app_settings", "kb_upsert_batch_size")
    op.drop_column("app_settings", "kb_chunk_overlap")
    op.drop_column("app_settings", "kb_chunk_size")
