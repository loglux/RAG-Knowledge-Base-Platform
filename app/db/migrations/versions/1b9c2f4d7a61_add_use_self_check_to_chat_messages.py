"""Add use_self_check to chat_messages

Revision ID: 1b9c2f4d7a61
Revises: 2f6c1a9b3d52
Create Date: 2026-02-03 03:35:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b9c2f4d7a61'
down_revision: Union[str, None] = '2f6c1a9b3d52'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration."""
    op.add_column(
        'chat_messages',
        sa.Column('use_self_check', sa.Boolean(), nullable=True, comment='Whether self-check was applied')
    )


def downgrade() -> None:
    """Revert migration."""
    op.drop_column('chat_messages', 'use_self_check')
