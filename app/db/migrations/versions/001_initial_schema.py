"""Initial schema - KnowledgeBase and Document tables

Revision ID: 001
Revises:
Create Date: 2026-01-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration."""
    # Create knowledge_bases table
    op.create_table(
        'knowledge_bases',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('collection_name', sa.String(length=255), nullable=False),
        sa.Column('chunk_size', sa.Integer(), nullable=False, server_default='1000'),
        sa.Column('chunk_overlap', sa.Integer(), nullable=False, server_default='200'),
        sa.Column(
            'chunking_strategy',
            sa.Enum('FIXED_SIZE', 'SEMANTIC', 'PARAGRAPH', name='chunkingstrategy'),
            nullable=False,
            server_default='FIXED_SIZE'
        ),
        sa.Column('document_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_chunks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment='Owner user ID - nullable for MVP, will be required later'
        ),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_knowledge_bases_name', 'knowledge_bases', ['name'])
    op.create_index('ix_knowledge_bases_user_id', 'knowledge_bases', ['user_id'])
    op.create_index('ix_knowledge_bases_collection_name', 'knowledge_bases', ['collection_name'], unique=True)

    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('knowledge_base_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column(
            'file_type',
            sa.Enum('txt', 'md', name='filetype'),
            nullable=False
        ),
        sa.Column('file_size', sa.Integer(), nullable=False, comment='File size in bytes'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column(
            'content_hash',
            sa.String(length=64),
            nullable=False,
            comment='SHA-256 hash of content for deduplication'
        ),
        sa.Column(
            'status',
            sa.Enum('pending', 'processing', 'completed', 'failed', name='documentstatus'),
            nullable=False,
            server_default='pending'
        ),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('chunk_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column(
            'vector_ids',
            sa.Text(),
            nullable=True,
            comment='Comma-separated list of Qdrant vector IDs'
        ),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment='Owner user ID - nullable for MVP'
        ),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['knowledge_base_id'],
            ['knowledge_bases.id'],
            ondelete='CASCADE'
        )
    )
    op.create_index('ix_documents_knowledge_base_id', 'documents', ['knowledge_base_id'])
    op.create_index('ix_documents_content_hash', 'documents', ['content_hash'])
    op.create_index('ix_documents_status', 'documents', ['status'])
    op.create_index('ix_documents_user_id', 'documents', ['user_id'])


def downgrade() -> None:
    """Revert migration."""
    op.drop_index('ix_documents_user_id', table_name='documents')
    op.drop_index('ix_documents_status', table_name='documents')
    op.drop_index('ix_documents_content_hash', table_name='documents')
    op.drop_index('ix_documents_knowledge_base_id', table_name='documents')
    op.drop_table('documents')

    op.drop_index('ix_knowledge_bases_collection_name', table_name='knowledge_bases')
    op.drop_index('ix_knowledge_bases_user_id', table_name='knowledge_bases')
    op.drop_index('ix_knowledge_bases_name', table_name='knowledge_bases')
    op.drop_table('knowledge_bases')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS documentstatus')
    op.execute('DROP TYPE IF EXISTS filetype')
    op.execute('DROP TYPE IF EXISTS chunkingstrategy')
