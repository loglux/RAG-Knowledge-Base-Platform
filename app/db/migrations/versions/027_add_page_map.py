"""Add page_map_json to documents.

Revision ID: 027
Revises: 026
Create Date: 2026-02-24
"""

import sqlalchemy as sa
from alembic import op

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "page_map_json",
            sa.Text(),
            nullable=True,
            comment="JSON [[char_offset, page_number], ...] for PDF page tracking",
        ),
    )


def downgrade() -> None:
    op.drop_column("documents", "page_map_json")
