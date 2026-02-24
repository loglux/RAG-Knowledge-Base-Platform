"""Add heading_map_json to documents table.

Revision ID: 025
Revises: 024
Create Date: 2026-02-24
"""

import sqlalchemy as sa
from alembic import op

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "heading_map_json",
            sa.Text(),
            nullable=True,
            comment="JSON-encoded heading map for structural metadata indexing (DOCX)",
        ),
    )


def downgrade() -> None:
    op.drop_column("documents", "heading_map_json")
