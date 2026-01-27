"""Add settings_json to conversations

Revision ID: 006
Revises: 005
Create Date: 2026-01-27
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add settings_json column to conversations."""
    op.add_column(
        'conversations',
        sa.Column('settings_json', sa.Text(), nullable=True)
    )


def downgrade() -> None:
    """Remove settings_json column from conversations."""
    op.drop_column('conversations', 'settings_json')
