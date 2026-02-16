"""Add app_settings table

Revision ID: 008
Revises: 007
Create Date: 2026-01-27
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create app_settings table."""
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("llm_model", sa.String(length=100), nullable=True),
        sa.Column("llm_provider", sa.String(length=50), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("top_k", sa.Integer(), nullable=True),
        sa.Column("max_context_chars", sa.Integer(), nullable=True),
        sa.Column("score_threshold", sa.Float(), nullable=True),
        sa.Column("use_structure", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    """Drop app_settings table."""
    op.drop_table("app_settings")
