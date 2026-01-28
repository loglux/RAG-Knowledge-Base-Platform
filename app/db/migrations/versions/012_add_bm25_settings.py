"""Add BM25 settings to app_settings and knowledge_bases

Revision ID: 012
Revises: 011
Create Date: 2026-01-28
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('app_settings', sa.Column('bm25_match_mode', sa.String(20), nullable=True))
    op.add_column('app_settings', sa.Column('bm25_min_should_match', sa.Integer(), nullable=True))
    op.add_column('app_settings', sa.Column('bm25_use_phrase', sa.Boolean(), nullable=True))
    op.add_column('app_settings', sa.Column('bm25_analyzer', sa.String(20), nullable=True))

    op.add_column('knowledge_bases', sa.Column('bm25_match_mode', sa.String(20), nullable=True))
    op.add_column('knowledge_bases', sa.Column('bm25_min_should_match', sa.Integer(), nullable=True))
    op.add_column('knowledge_bases', sa.Column('bm25_use_phrase', sa.Boolean(), nullable=True))
    op.add_column('knowledge_bases', sa.Column('bm25_analyzer', sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column('knowledge_bases', 'bm25_analyzer')
    op.drop_column('knowledge_bases', 'bm25_use_phrase')
    op.drop_column('knowledge_bases', 'bm25_min_should_match')
    op.drop_column('knowledge_bases', 'bm25_match_mode')

    op.drop_column('app_settings', 'bm25_analyzer')
    op.drop_column('app_settings', 'bm25_use_phrase')
    op.drop_column('app_settings', 'bm25_min_should_match')
    op.drop_column('app_settings', 'bm25_match_mode')
