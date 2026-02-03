"""Add fb2 to filetype enum.

Revision ID: 9b2f3c6a7d11
Revises: 8e2c4a1b7f10
Create Date: 2026-02-03 13:00:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "9b2f3c6a7d11"
down_revision = "8e2c4a1b7f10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE filetype ADD VALUE IF NOT EXISTS 'fb2'")


def downgrade() -> None:
    # Downgrade not supported for enum value removal
    pass
