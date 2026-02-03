"""Merge heads 014 and 0f3b9f7a1c9a

Revision ID: 2f6c1a9b3d52
Revises: 014, 0f3b9f7a1c9a
Create Date: 2026-02-03 03:20:00

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = '2f6c1a9b3d52'
down_revision: Union[str, Sequence[str], None] = ('014', '0f3b9f7a1c9a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge heads (no-op)."""
    pass


def downgrade() -> None:
    """Revert merge (no-op)."""
    pass
