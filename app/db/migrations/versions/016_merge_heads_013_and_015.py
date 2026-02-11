"""Merge heads 013 and 015

Revision ID: 016
Revises: 013, 015
Create Date: 2026-02-10
"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = '016'
down_revision: Union[str, Sequence[str], None] = ('013', '015')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge heads (no-op)."""
    pass


def downgrade() -> None:
    """Revert merge (no-op)."""
    pass
