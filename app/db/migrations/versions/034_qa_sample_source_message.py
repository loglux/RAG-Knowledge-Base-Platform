"""Link gold samples back to the chat message they were promoted from.

Closes the chat → eval loop: when an assistant message is rated 👍 the API
auto-creates a qa_sample, and this column lets us find/update/delete that
sample when the rating changes. Nullable so existing uploaded samples
(no chat origin) stay valid.

Revision ID: 034
Revises: 033
Create Date: 2026-05-16
"""

import sqlalchemy as sa
from alembic import op

revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "qa_samples",
        sa.Column(
            "source_message_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Chat message this gold sample was promoted from, if any",
        ),
    )
    op.create_foreign_key(
        "qa_samples_source_message_id_fkey",
        "qa_samples",
        "chat_messages",
        ["source_message_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_qa_samples_source_message",
        "qa_samples",
        ["source_message_id"],
        unique=True,
        postgresql_where=sa.text("source_message_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_qa_samples_source_message", table_name="qa_samples")
    op.drop_constraint("qa_samples_source_message_id_fkey", "qa_samples", type_="foreignkey")
    op.drop_column("qa_samples", "source_message_id")
