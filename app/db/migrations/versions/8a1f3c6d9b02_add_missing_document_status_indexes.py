"""add missing document status indexes

Revision ID: 8a1f3c6d9b02
Revises: 23089df6c356
Create Date: 2026-10-20 19:35:00.000000

The models (app/models/database.py) declare index=True on
Document.embeddings_status and Document.bm25_status, but no migration ever
actually created those indexes - found via a diff against a fresh
`alembic revision --autogenerate`, which also surfaced ~150 unrelated
index-rename/comment/server_default mismatches accumulated from manual DB
tweaks over time. Those are purely cosmetic (same columns, old vs. new
auto-generated names) and are deliberately NOT included here - reconciling
them is a separate, lower-risk-tolerance cleanup, not bundled with a real
schema change. These two are the only genuinely missing indexes.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8a1f3c6d9b02"
down_revision: Union[str, None] = "23089df6c356"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration."""
    op.create_index(
        op.f("ix_documents_embeddings_status"), "documents", ["embeddings_status"], unique=False
    )
    op.create_index(op.f("ix_documents_bm25_status"), "documents", ["bm25_status"], unique=False)


def downgrade() -> None:
    """Revert migration."""
    op.drop_index(op.f("ix_documents_bm25_status"), table_name="documents")
    op.drop_index(op.f("ix_documents_embeddings_status"), table_name="documents")
