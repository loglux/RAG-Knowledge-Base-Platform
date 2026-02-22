"""Add reranking settings to app_settings

Revision ID: 022
Revises: 021, 1b9c2f4d7a61
Create Date: 2026-02-22 12:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "022"
down_revision = ("021", "1b9c2f4d7a61")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("app_settings", sa.Column("rerank_enabled", sa.Boolean(), nullable=True))
    op.add_column("app_settings", sa.Column("rerank_provider", sa.String(length=50), nullable=True))
    op.add_column("app_settings", sa.Column("rerank_model", sa.String(length=100), nullable=True))
    op.add_column("app_settings", sa.Column("rerank_candidate_pool", sa.Integer(), nullable=True))
    op.add_column("app_settings", sa.Column("rerank_top_n", sa.Integer(), nullable=True))
    op.add_column("app_settings", sa.Column("rerank_min_score", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("app_settings", "rerank_min_score")
    op.drop_column("app_settings", "rerank_top_n")
    op.drop_column("app_settings", "rerank_candidate_pool")
    op.drop_column("app_settings", "rerank_model")
    op.drop_column("app_settings", "rerank_provider")
    op.drop_column("app_settings", "rerank_enabled")
