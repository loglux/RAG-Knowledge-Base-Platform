"""Merge heads 016 and fa1b2c3d4e5f

Revision ID: 017
Revises: 016, fa1b2c3d4e5f
Create Date: 2026-02-10
"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = '017'
down_revision: Union[str, Sequence[str], None] = (
    '016',
    'fa1b2c3d4e5f',
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge heads (no-op)."""
    pass


def downgrade() -> None:
    """Revert merge (no-op)."""
    pass
