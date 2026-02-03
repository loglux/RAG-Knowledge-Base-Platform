"""Add admin refresh tokens

Revision ID: 8e2c4a1b7f10
Revises: 6c3f8a2d1b4e
Create Date: 2026-02-03 11:20:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '8e2c4a1b7f10'
down_revision: Union[str, None] = '6c3f8a2d1b4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration."""
    op.create_table(
        'admin_refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('admin_user_id', sa.Integer(), sa.ForeignKey('admin_users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('jti', sa.String(length=36), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_admin_refresh_tokens_admin_user_id', 'admin_refresh_tokens', ['admin_user_id'])
    op.create_index('ix_admin_refresh_tokens_jti', 'admin_refresh_tokens', ['jti'], unique=True)


def downgrade() -> None:
    """Revert migration."""
    op.drop_index('ix_admin_refresh_tokens_jti', table_name='admin_refresh_tokens')
    op.drop_index('ix_admin_refresh_tokens_admin_user_id', table_name='admin_refresh_tokens')
    op.drop_table('admin_refresh_tokens')
