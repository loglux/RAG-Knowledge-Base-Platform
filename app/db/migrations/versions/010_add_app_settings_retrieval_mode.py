"""Add retrieval mode settings to app_settings

Revision ID: 010
Revises: 009
Create Date: 2026-01-28
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add retrieval mode columns."""
    op.add_column("app_settings", sa.Column("retrieval_mode", sa.String(length=20), nullable=True))
    op.add_column("app_settings", sa.Column("lexical_top_k", sa.Integer(), nullable=True))
    op.add_column("app_settings", sa.Column("hybrid_dense_weight", sa.Float(), nullable=True))
    op.add_column("app_settings", sa.Column("hybrid_lexical_weight", sa.Float(), nullable=True))


def downgrade() -> None:
    """Remove retrieval mode columns."""
    op.drop_column("app_settings", "hybrid_lexical_weight")
    op.drop_column("app_settings", "hybrid_dense_weight")
    op.drop_column("app_settings", "lexical_top_k")
    op.drop_column("app_settings", "retrieval_mode")
