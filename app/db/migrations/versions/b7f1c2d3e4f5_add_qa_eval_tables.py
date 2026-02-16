"""Add QA evaluation tables.

Revision ID: b7f1c2d3e4f5
Revises: 9b2f3c6a7d11
Create Date: 2026-02-03 13:30:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b7f1c2d3e4f5"
down_revision = "9b2f3c6a7d11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "qa_samples",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=True),
        sa.Column("source_span", sa.Text(), nullable=True),
        sa.Column("sample_type", sa.String(length=20), nullable=False, server_default="gold"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_qa_samples_kb", "qa_samples", ["knowledge_base_id"])
    op.create_index("ix_qa_samples_document", "qa_samples", ["document_id"])
    op.create_index("ix_qa_samples_type", "qa_samples", ["sample_type"])

    op.create_table(
        "qa_eval_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False, server_default="gold"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("config_json", sa.Text(), nullable=True),
        sa.Column("metrics_json", sa.Text(), nullable=True),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_qa_eval_runs_kb", "qa_eval_runs", ["knowledge_base_id"])

    op.create_table(
        "qa_eval_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sample_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("sources_json", sa.Text(), nullable=True),
        sa.Column("metrics_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["qa_eval_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sample_id"], ["qa_samples.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_qa_eval_results_run", "qa_eval_results", ["run_id"])
    op.create_index("ix_qa_eval_results_sample", "qa_eval_results", ["sample_id"])


def downgrade() -> None:
    op.drop_index("ix_qa_eval_results_sample", table_name="qa_eval_results")
    op.drop_index("ix_qa_eval_results_run", table_name="qa_eval_results")
    op.drop_table("qa_eval_results")

    op.drop_index("ix_qa_eval_runs_kb", table_name="qa_eval_runs")
    op.drop_table("qa_eval_runs")

    op.drop_index("ix_qa_samples_type", table_name="qa_samples")
    op.drop_index("ix_qa_samples_document", table_name="qa_samples")
    op.drop_index("ix_qa_samples_kb", table_name="qa_samples")
    op.drop_table("qa_samples")
