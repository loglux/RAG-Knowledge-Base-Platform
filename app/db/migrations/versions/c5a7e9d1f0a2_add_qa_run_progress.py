"""Add processed_count to QA eval runs.

Revision ID: c5a7e9d1f0a2
Revises: b7f1c2d3e4f5
Create Date: 2026-02-03 17:30:00.000000
"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "c5a7e9d1f0a2"
down_revision = "b7f1c2d3e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("qa_eval_runs", sa.Column("processed_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("qa_eval_runs", "processed_count")
