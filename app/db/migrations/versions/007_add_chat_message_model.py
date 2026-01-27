"""Add model column to chat_messages

Revision ID: 007
Revises: 006
Create Date: 2026-01-27
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add model column to chat_messages."""
    op.add_column(
        'chat_messages',
        sa.Column('model', sa.String(length=100), nullable=True)
    )


def downgrade() -> None:
    """Remove model column from chat_messages."""
    op.drop_column('chat_messages', 'model')
