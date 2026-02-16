"""Add prompt versioning tables and settings.

Revision ID: a6c4d2e9f1b3
Revises: f4a5b6c7d8e9
Create Date: 2026-02-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a6c4d2e9f1b3"
down_revision: Union[str, None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration."""
    op.create_table(
        "prompt_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Creator user ID (nullable for MVP)",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_prompt_versions_created_by", "prompt_versions", ["created_by"])

    op.add_column(
        "chat_messages",
        sa.Column(
            "prompt_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Prompt version used to generate this message",
        ),
    )
    op.create_foreign_key(
        "fk_chat_messages_prompt_version_id",
        "chat_messages",
        "prompt_versions",
        ["prompt_version_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "app_settings",
        sa.Column(
            "active_prompt_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Active prompt version for RAG system prompt",
        ),
    )
    op.add_column(
        "app_settings",
        sa.Column(
            "show_prompt_versions",
            sa.Boolean(),
            nullable=True,
            comment="Whether to display prompt version in chat responses",
        ),
    )
    op.create_foreign_key(
        "fk_app_settings_active_prompt_version_id",
        "app_settings",
        "prompt_versions",
        ["active_prompt_version_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Revert migration."""
    op.drop_constraint(
        "fk_app_settings_active_prompt_version_id", "app_settings", type_="foreignkey"
    )
    op.drop_column("app_settings", "show_prompt_versions")
    op.drop_column("app_settings", "active_prompt_version_id")

    op.drop_constraint("fk_chat_messages_prompt_version_id", "chat_messages", type_="foreignkey")
    op.drop_column("chat_messages", "prompt_version_id")

    op.drop_index("ix_prompt_versions_created_by", table_name="prompt_versions")
    op.drop_table("prompt_versions")
