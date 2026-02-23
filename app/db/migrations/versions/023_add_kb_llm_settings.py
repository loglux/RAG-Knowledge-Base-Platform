"""Add KB-level LLM settings and AppSettings use_self_check.

Revision ID: 023
Revises: 022
Create Date: 2026-02-23
"""

import sqlalchemy as sa
from alembic import op

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # knowledge_bases: KB-level LLM overrides
    op.add_column("knowledge_bases", sa.Column("llm_model", sa.String(100), nullable=True))
    op.add_column("knowledge_bases", sa.Column("llm_provider", sa.String(50), nullable=True))
    op.add_column("knowledge_bases", sa.Column("temperature", sa.Float(), nullable=True))
    op.add_column("knowledge_bases", sa.Column("use_self_check", sa.Boolean(), nullable=True))

    # app_settings: global use_self_check default
    op.add_column("app_settings", sa.Column("use_self_check", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("app_settings", "use_self_check")
    op.drop_column("knowledge_bases", "use_self_check")
    op.drop_column("knowledge_bases", "temperature")
    op.drop_column("knowledge_bases", "llm_provider")
    op.drop_column("knowledge_bases", "llm_model")
