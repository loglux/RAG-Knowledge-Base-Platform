"""Add docx to filetype enum.

Revision ID: d4a1c9f2e6b7
Revises: c5a7e9d1f0a2
Create Date: 2026-02-04 15:05:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "d4a1c9f2e6b7"
down_revision = "c5a7e9d1f0a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE filetype ADD VALUE IF NOT EXISTS 'docx'")


def downgrade() -> None:
    # Downgrade is a no-op because removing enum values is not supported safely.
    pass
