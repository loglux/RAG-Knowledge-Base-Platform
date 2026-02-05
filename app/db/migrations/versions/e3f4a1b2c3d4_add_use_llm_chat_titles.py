"""add use_llm_chat_titles to app_settings

Revision ID: e3f4a1b2c3d4
Revises: d4a1c9f2e6b7
Create Date: 2026-02-05
"""
from typing import Union, Sequence
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e3f4a1b2c3d4'
down_revision: Union[str, None] = 'd4a1c9f2e6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('app_settings', sa.Column('use_llm_chat_titles', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('app_settings', 'use_llm_chat_titles')
