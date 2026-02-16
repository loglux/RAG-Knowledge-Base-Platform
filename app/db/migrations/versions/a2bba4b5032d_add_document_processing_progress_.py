"""Add document processing progress tracking

Revision ID: a2bba4b5032d
Revises: 031d3e796cb8
Create Date: 2026-02-01 12:14:14.486625

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2bba4b5032d"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration."""
    # Add processing progress tracking columns
    op.add_column(
        "documents",
        sa.Column(
            "processing_stage",
            sa.String(length=100),
            nullable=True,
            comment="Current processing stage (e.g., Chunking, Embedding 50/100)",
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "progress_percentage",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Processing progress 0-100%",
        ),
    )


def downgrade() -> None:
    """Revert migration."""
    # Remove processing progress tracking columns
    op.drop_column("documents", "progress_percentage")
    op.drop_column("documents", "processing_stage")
