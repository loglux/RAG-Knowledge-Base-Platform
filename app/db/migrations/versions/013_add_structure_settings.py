"""Add structure model and TOC rate limit settings.

Revision ID: 013
Revises: 012
Create Date: 2026-01-28
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("knowledge_bases", sa.Column("structure_llm_model", sa.String(length=100), nullable=True))
    op.add_column("app_settings", sa.Column("structure_requests_per_minute", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("app_settings", "structure_requests_per_minute")
    op.drop_column("knowledge_bases", "structure_llm_model")
