"""Add new chunking strategy enum values

Revision ID: 031d3e796cb8
Revises: 013
Create Date: 2026-01-31 11:48:52.247790

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '031d3e796cb8'
down_revision: Union[str, None] = '013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration.

    Note: This migration adds new values to the chunkingstrategy enum.
    ALTER TYPE ADD VALUE cannot run inside a transaction block, so these
    commands must be run manually via psql:

    docker exec kb-platform-db psql -U kb_user -d knowledge_base -c "ALTER TYPE chunkingstrategy ADD VALUE IF NOT EXISTS 'simple';"
    docker exec kb-platform-db psql -U kb_user -d knowledge_base -c "ALTER TYPE chunkingstrategy ADD VALUE IF NOT EXISTS 'smart';"
    docker exec kb-platform-db psql -U kb_user -d knowledge_base -c "ALTER TYPE chunkingstrategy ADD VALUE IF NOT EXISTS 'semantic';"

    The chunkingstrategy enum now has 5 values:
    - FIXED_SIZE (legacy, maps to simple)
    - PARAGRAPH (legacy, maps to smart)
    - simple (new, fixed-size chunking)
    - smart (new, recursive/paragraph-aware chunking)
    - semantic (new, future semantic chunking with embeddings)
    """
    # Commands run manually - this migration serves as documentation
    pass


def downgrade() -> None:
    """Revert migration.

    Note: PostgreSQL does not support removing enum values easily.
    This would require creating a new enum type and migrating data.
    For development, if needed, recreate the database.
    """
    pass
