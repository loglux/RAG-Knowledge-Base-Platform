"""Add embedding provider configuration to knowledge bases

Revision ID: 002
Revises: 001
Create Date: 2026-01-24 23:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add embedding configuration columns to knowledge_bases table
    op.add_column(
        'knowledge_bases',
        sa.Column(
            'embedding_model',
            sa.String(length=100),
            nullable=False,
            server_default='text-embedding-3-large',
            comment='Embedding model name (e.g., text-embedding-3-large, voyage-4)'
        )
    )
    op.add_column(
        'knowledge_bases',
        sa.Column(
            'embedding_provider',
            sa.String(length=50),
            nullable=False,
            server_default='openai',
            comment='Embedding provider (openai, voyage)'
        )
    )
    op.add_column(
        'knowledge_bases',
        sa.Column(
            'embedding_dimension',
            sa.Integer(),
            nullable=False,
            server_default='3072',
            comment='Vector dimension size for embeddings'
        )
    )


def downgrade() -> None:
    # Remove embedding configuration columns
    op.drop_column('knowledge_bases', 'embedding_dimension')
    op.drop_column('knowledge_bases', 'embedding_provider')
    op.drop_column('knowledge_bases', 'embedding_model')
