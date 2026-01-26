"""Add document_structure table for TOC

Revision ID: 003
Revises: 002
Create Date: 2026-01-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add document_structures table."""
    op.create_table(
        'document_structures',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            'document_id',
            UUID(as_uuid=True),
            sa.ForeignKey('documents.id', ondelete='CASCADE'),
            nullable=False,
            unique=True
        ),
        sa.Column('toc_json', sa.Text(), nullable=False, comment='Hierarchical table of contents in JSON format'),
        sa.Column('document_type', sa.String(100), nullable=True, comment='Document type detected by LLM'),
        sa.Column('approved_by_user', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Create indexes
    op.create_index('ix_document_structures_document_id', 'document_structures', ['document_id'])


def downgrade() -> None:
    """Remove document_structures table."""
    op.drop_index('ix_document_structures_document_id', table_name='document_structures')
    op.drop_table('document_structures')
