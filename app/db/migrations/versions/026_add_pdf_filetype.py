"""Add pdf to filetype enum.

Revision ID: 026
Revises: 025
Create Date: 2026-02-24
"""

from alembic import op

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE filetype ADD VALUE IF NOT EXISTS 'pdf'")


def downgrade() -> None:
    # Enum value removal not supported in PostgreSQL without recreating the type
    pass
