"""Add self-check prompt versions and active setting.

Revision ID: a8b1c2d3e4f6
Revises: a7c8d9e0f1a2
Create Date: 2026-02-05
"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "a8b1c2d3e4f6"
down_revision: Union[str, None] = "a7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULT_SELF_CHECK_SYSTEM_PROMPT = """You are validating an answer produced by a Retrieval-Augmented Generation (RAG) system.

Instructions:
1. Analyze what the question requires (e.g., single passage, multiple passages, summary, specific information)
2. Verify that the answer appropriately addresses this requirement
3. Ensure every factual statement in the answer is explicitly supported by the retrieved context
4. Check that the answer does not add information not present in the context
5. If the question asks for a specific passage, the answer must rely on that passage alone and must not incorporate details from later or separate passages
6. If the answer is satisfactory, return it unchanged
7. If improvements are needed, rewrite the answer to be more accurate and better grounded in the context

Output only the final answer (do not include explanations or meta-commentary)."""

DEFAULT_SELF_CHECK_USER_TEMPLATE = """Question: {{question}}

Draft Answer: {{draft_answer}}

Retrieved Context:
{{context}}"""


def upgrade() -> None:
    """Apply migration."""
    op.create_table(
        "self_check_prompt_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("system_content", sa.Text(), nullable=False),
        sa.Column("user_template", sa.Text(), nullable=False),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Creator user ID (nullable for MVP)",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_self_check_prompt_versions_created_by", "self_check_prompt_versions", ["created_by"])

    op.add_column(
        "app_settings",
        sa.Column(
            "active_self_check_prompt_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Active prompt version for self-check validation",
        ),
    )
    op.create_foreign_key(
        "fk_app_settings_active_self_check_prompt_version_id",
        "app_settings",
        "self_check_prompt_versions",
        ["active_self_check_prompt_version_id"],
        ["id"],
        ondelete="SET NULL",
    )

    prompt_id = str(uuid.uuid4())
    op.execute(
        sa.text(
            """
            INSERT INTO self_check_prompt_versions (id, name, system_content, user_template, created_by, created_at)
            SELECT CAST(:prompt_id AS uuid), 'Self-Check Prompt', :system_content, :user_template, NULL, now()
            WHERE NOT EXISTS (SELECT 1 FROM self_check_prompt_versions);
            """
        ).bindparams(
            prompt_id=prompt_id,
            system_content=DEFAULT_SELF_CHECK_SYSTEM_PROMPT,
            user_template=DEFAULT_SELF_CHECK_USER_TEMPLATE,
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE app_settings
            SET active_self_check_prompt_version_id = (
                SELECT id FROM self_check_prompt_versions ORDER BY created_at DESC LIMIT 1
            )
            WHERE active_self_check_prompt_version_id IS NULL;
            """
        )
    )


def downgrade() -> None:
    """Revert migration."""
    op.drop_constraint(
        "fk_app_settings_active_self_check_prompt_version_id",
        "app_settings",
        type_="foreignkey",
    )
    op.drop_column("app_settings", "active_self_check_prompt_version_id")
    op.drop_index("ix_self_check_prompt_versions_created_by", table_name="self_check_prompt_versions")
    op.drop_table("self_check_prompt_versions")
