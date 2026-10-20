"""add url_crawl_jobs table

Revision ID: 23089df6c356
Revises: 036
Create Date: 2026-10-20 18:35:54.999012

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "23089df6c356"
down_revision: Union[str, None] = "036"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration."""
    op.create_table(
        "url_crawl_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("knowledge_base_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True, comment="Owner user ID - nullable for MVP"),
        sa.Column("seed_url", sa.String(length=2048), nullable=False),
        sa.Column(
            "scope",
            sa.String(length=20),
            nullable=False,
            comment="domain | path_prefix | unrestricted",
        ),
        sa.Column("max_depth", sa.Integer(), nullable=False),
        sa.Column("max_pages", sa.Integer(), nullable=False),
        sa.Column("detect_duplicates", sa.Boolean(), nullable=False),
        sa.Column("contextual_description_enabled", sa.Boolean(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            comment="pending | running | completed | failed",
        ),
        sa.Column("pages_discovered", sa.Integer(), nullable=False),
        sa.Column("pages_processed", sa.Integer(), nullable=False),
        sa.Column("pages_duplicate", sa.Integer(), nullable=False),
        sa.Column("pages_failed", sa.Integer(), nullable=False),
        sa.Column(
            "pages_json",
            sa.Text(),
            nullable=True,
            comment="JSON array of {url, depth, status, document_id, error}",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="Fatal error if the job failed before processing any page",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_url_crawl_jobs_knowledge_base_id"),
        "url_crawl_jobs",
        ["knowledge_base_id"],
        unique=False,
    )
    op.create_index(op.f("ix_url_crawl_jobs_status"), "url_crawl_jobs", ["status"], unique=False)
    op.create_index(op.f("ix_url_crawl_jobs_user_id"), "url_crawl_jobs", ["user_id"], unique=False)


def downgrade() -> None:
    """Revert migration."""
    op.drop_index(op.f("ix_url_crawl_jobs_user_id"), table_name="url_crawl_jobs")
    op.drop_index(op.f("ix_url_crawl_jobs_status"), table_name="url_crawl_jobs")
    op.drop_index(op.f("ix_url_crawl_jobs_knowledge_base_id"), table_name="url_crawl_jobs")
    op.drop_table("url_crawl_jobs")
