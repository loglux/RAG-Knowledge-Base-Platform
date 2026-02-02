"""Add admin_users and system_settings tables for Setup Wizard

Revision ID: 014
Revises: a2bba4b5032d
Create Date: 2026-02-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '014'
down_revision: Union[str, None] = 'a2bba4b5032d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create admin_users and system_settings tables."""

    # Create admin_users table
    op.create_table(
        'admin_users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('username', sa.String(length=100), nullable=False, unique=True, index=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False,
                  comment='Bcrypt password hash'),
        sa.Column('email', sa.String(length=255), nullable=True, index=True),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='admin',
                  comment='User role: admin, superadmin'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_login', sa.DateTime(), nullable=True),
    )

    # Create system_settings table
    op.create_table(
        'system_settings',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('key', sa.String(length=255), nullable=False, unique=True, index=True,
                  comment="Setting key (e.g., 'openai_api_key', 'qdrant_url')"),
        sa.Column('value', sa.Text(), nullable=True,
                  comment='Setting value (encrypted if is_encrypted=True)'),
        sa.Column('is_encrypted', sa.Boolean(), nullable=False, server_default='false',
                  comment='Whether value is encrypted (for API keys, passwords)'),
        sa.Column('category', sa.String(length=100), nullable=False, index=True,
                  comment='Setting category: api, database, system, limits'),
        sa.Column('description', sa.Text(), nullable=True,
                  comment='Human-readable description of the setting'),
        sa.Column('updated_by', sa.Integer(), nullable=True,
                  comment='Admin user who last updated this setting'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # Add foreign key for updated_by
    op.create_foreign_key(
        'fk_system_settings_updated_by',
        'system_settings', 'admin_users',
        ['updated_by'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Drop admin_users and system_settings tables."""

    # Drop foreign key first
    op.drop_constraint('fk_system_settings_updated_by', 'system_settings', type_='foreignkey')

    # Drop tables
    op.drop_table('system_settings')
    op.drop_table('admin_users')
