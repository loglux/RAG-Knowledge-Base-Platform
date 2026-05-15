"""Add PDF parsing overrides to app_settings and knowledge_bases.

Three knobs surfaced to admin UI: table strategy, heading-size sensitivity,
and minimum extracted text length. All nullable everywhere — None means
"use built-in default" (KB) or "use built-in default" (app).

Revision ID: 032
Revises: 031
Create Date: 2026-05-16
"""

import sqlalchemy as sa
from alembic import op

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("app_settings", "knowledge_bases"):
        op.add_column(
            table,
            sa.Column(
                "pdf_table_strategy",
                sa.String(length=10),
                nullable=True,
                comment="PyMuPDF find_tables strategy: 'lines' or 'text'",
            ),
        )
        op.add_column(
            table,
            sa.Column(
                "pdf_heading_size_sensitivity",
                sa.Float(),
                nullable=True,
                comment=(
                    "Font-size ratio above which a block becomes a heading "
                    "(default 1.15). Lower = more aggressive."
                ),
            ),
        )
        op.add_column(
            table,
            sa.Column(
                "pdf_min_doc_length",
                sa.Integer(),
                nullable=True,
                comment=(
                    "Minimum chars after extraction; below this we reject the PDF "
                    "as likely scanned (default 100)."
                ),
            ),
        )


def downgrade() -> None:
    for table in ("knowledge_bases", "app_settings"):
        op.drop_column(table, "pdf_min_doc_length")
        op.drop_column(table, "pdf_heading_size_sensitivity")
        op.drop_column(table, "pdf_table_strategy")
