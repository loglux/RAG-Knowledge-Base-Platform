"""Remove legacy database_url system setting

Revision ID: 6c3f8a2d1b4e
Revises: 1b9c2f4d7a61
Create Date: 2026-02-03 03:55:00

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6c3f8a2d1b4e"
down_revision: Union[str, None] = "1b9c2f4d7a61"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration."""
    op.execute("DELETE FROM system_settings WHERE key = 'database_url';")


def downgrade() -> None:
    """Revert migration."""
    pass
