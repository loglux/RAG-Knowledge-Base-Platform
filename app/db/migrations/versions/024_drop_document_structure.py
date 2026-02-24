"""Drop document structure feature tables and columns.

Revision ID: 024
Revises: 023
Create Date: 2026-02-24
"""

import sqlalchemy as sa
from alembic import op

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop document_structures table (created in migration 003)
    op.drop_index("ix_document_structures_document_id", table_name="document_structures")
    op.drop_table("document_structures")

    # Drop structure_llm_model from knowledge_bases (added in migration 013)
    op.drop_column("knowledge_bases", "structure_llm_model")

    # Drop structure-related columns from app_settings
    op.drop_column("app_settings", "use_structure")
    op.drop_column("app_settings", "structure_requests_per_minute")


def downgrade() -> None:
    op.add_column(
        "app_settings",
        sa.Column("structure_requests_per_minute", sa.Integer(), nullable=True),
    )
    op.add_column(
        "app_settings",
        sa.Column("use_structure", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "knowledge_bases",
        sa.Column("structure_llm_model", sa.String(100), nullable=True),
    )
    op.create_table(
        "document_structures",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("toc_json", sa.Text(), nullable=True),
        sa.Column("document_type", sa.String(50), nullable=True),
        sa.Column("approved_by_user", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_structures_document_id",
        "document_structures",
        ["document_id"],
    )
