"""merge heads a9b2c3d4e5f7 and f9c1a2b3c4d5

Revision ID: fa1b2c3d4e5f
Revises: a9b2c3d4e5f7, f9c1a2b3c4d5
Create Date: 2026-02-06
"""
from typing import Union, Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fa1b2c3d4e5f"
down_revision: Union[str, tuple[str, str], None] = ("a9b2c3d4e5f7", "f9c1a2b3c4d5")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
