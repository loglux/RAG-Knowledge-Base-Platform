"""Add language column to documents table."""

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op


def upgrade():
    op.add_column(
        "documents",
        sa.Column(
            "language", sa.String(length=10), nullable=True, comment="ISO 639-1 language code"
        ),
    )


def downgrade():
    op.drop_column("documents", "language")
