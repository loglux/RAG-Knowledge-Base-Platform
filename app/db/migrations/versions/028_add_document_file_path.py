"""Add file_path column to documents table."""

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op


def upgrade():
    op.add_column("documents", sa.Column("file_path", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("documents", "file_path")
