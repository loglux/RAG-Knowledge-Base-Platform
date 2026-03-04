"""Add contextual description settings to app and KB.

Revision ID: 030
Revises: 029
Create Date: 2026-03-04
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "app_settings",
        sa.Column(
            "contextual_description_enabled",
            sa.Boolean(),
            nullable=True,
            comment="Global default for contextual description generation during ingestion",
        ),
    )
    op.add_column(
        "knowledge_bases",
        sa.Column(
            "contextual_description_enabled",
            sa.Boolean(),
            nullable=True,
            comment="KB-level toggle for contextual description generation during ingestion",
        ),
    )


def downgrade() -> None:
    op.drop_column("knowledge_bases", "contextual_description_enabled")
    op.drop_column("app_settings", "contextual_description_enabled")
