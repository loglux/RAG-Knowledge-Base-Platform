"""Add source_url and web_metadata columns to documents.

Revision ID: 035
Revises: 034
Create Date: 2026-05-17
"""

import sqlalchemy as sa
from alembic import op

revision = "035"
down_revision = "034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "source_url",
            sa.String(2048),
            nullable=True,
            comment="Original URL for web-imported documents",
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "web_metadata",
            sa.Text(),
            nullable=True,
            comment="JSON: author, publish_date, sitename, description, canonical_url",
        ),
    )


def downgrade() -> None:
    op.drop_column("documents", "web_metadata")
    op.drop_column("documents", "source_url")
