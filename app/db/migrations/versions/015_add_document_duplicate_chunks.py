"""add document duplicate chunks

Revision ID: 015
Revises: d4a1c9f2e6b7
Create Date: 2026-02-08
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "015"
down_revision = "d4a1c9f2e6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("duplicate_chunks_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "duplicate_chunks_json")
