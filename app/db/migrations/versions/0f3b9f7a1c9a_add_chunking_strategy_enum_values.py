"""Add new chunking strategy enum values safely

Revision ID: 0f3b9f7a1c9a
Revises: a2bba4b5032d
Create Date: 2026-02-03 03:10:00

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '0f3b9f7a1c9a'
down_revision: Union[str, None] = 'a2bba4b5032d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration."""
    # ALTER TYPE ADD VALUE cannot run inside a transaction block
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE chunkingstrategy ADD VALUE IF NOT EXISTS 'simple';")
        op.execute("ALTER TYPE chunkingstrategy ADD VALUE IF NOT EXISTS 'smart';")
        op.execute("ALTER TYPE chunkingstrategy ADD VALUE IF NOT EXISTS 'semantic';")


def downgrade() -> None:
    """Revert migration.

    PostgreSQL does not support removing enum values easily.
    """
    pass
