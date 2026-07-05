"""Add consumed_upload_tokens table for presigned upload URL single-use tracking.

Revision ID: 036
Revises: 035
Create Date: 2026-07-05
"""

import sqlalchemy as sa
from alembic import op

revision = "036"
down_revision = "035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "consumed_upload_tokens",
        sa.Column("upload_id", sa.String(64), primary_key=True),
        sa.Column("consumed_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("consumed_upload_tokens")
