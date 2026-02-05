"""Add system_content and user_template to prompt_versions.

Revision ID: a7c8d9e0f1a2
Revises: a6c4d2e9f1b3
Create Date: 2026-02-05
"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7c8d9e0f1a2"
down_revision: Union[str, None] = "a6c4d2e9f1b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULT_SYSTEM_PROMPT = """Identity:
You are a retrieval assistant for a knowledge base. You answer ONLY from the provided context.

You are a helpful AI assistant that answers questions based on the provided context from a knowledge base.

Your task:
1. First, understand the FULL CONVERSATION HISTORY to grasp what the user is asking about
2. Pay attention to pronouns (it, this, that, these) - they often refer to topics from previous messages
3. Use the knowledge base context to provide accurate, detailed answers
4. Answer based ONLY on information from the knowledge base context
5. Be concise unless the user asks to show/quote content or examples
6. Reference specific sources when appropriate (e.g., "According to Source 1...")

Important:
- The conversation may contain follow-up questions - use previous messages to understand the current question
- Pronouns like "it", "this", "that" refer to topics mentioned earlier in the conversation
- Do NOT make up information not present in the context
- If the context doesn't contain enough information, say so clearly
- If the user asks to show a question, return the full verbatim text from the context.
- If the requested item spans multiple context chunks, return all relevant verbatim excerpts,
  even if they come from multiple chunks, until the item is complete.
- Do not invent missing parts or add commentary.

Context follows below.
"""

DEFAULT_USER_TEMPLATE = """<context>
{{context}}
</context>

<question>{{question}}{{show_question_instructions}}</question>

Answer based on the context above:"""


def upgrade() -> None:
    """Apply migration."""
    op.add_column("prompt_versions", sa.Column("system_content", sa.Text(), nullable=True))
    op.add_column("prompt_versions", sa.Column("user_template", sa.Text(), nullable=True))

    # Backfill existing rows
    op.execute(
        sa.text(
            """
            UPDATE prompt_versions
            SET system_content = content
            WHERE system_content IS NULL;
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE prompt_versions
            SET user_template = :template
            WHERE user_template IS NULL;
            """
        ).bindparams(template=DEFAULT_USER_TEMPLATE)
    )

    # Seed default prompt version if none exist
    prompt_id = str(uuid.uuid4())
    op.execute(
        sa.text(
            """
            INSERT INTO prompt_versions (id, name, content, system_content, user_template, created_by, created_at)
            SELECT CAST(:prompt_id AS uuid), 'Default Prompt', :system_content, :system_content, :user_template, NULL, now()
            WHERE NOT EXISTS (SELECT 1 FROM prompt_versions);
            """
        ).bindparams(
            prompt_id=prompt_id,
            system_content=DEFAULT_SYSTEM_PROMPT,
            user_template=DEFAULT_USER_TEMPLATE,
        )
    )

    op.alter_column("prompt_versions", "system_content", nullable=False)
    op.alter_column("prompt_versions", "user_template", nullable=False)

    op.drop_column("prompt_versions", "content")

    # Ensure app_settings has an active prompt if missing
    op.execute(
        sa.text(
            """
            UPDATE app_settings
            SET active_prompt_version_id = (
                SELECT id FROM prompt_versions ORDER BY created_at DESC LIMIT 1
            )
            WHERE active_prompt_version_id IS NULL;
            """
        )
    )


def downgrade() -> None:
    """Revert migration."""
    op.add_column("prompt_versions", sa.Column("content", sa.Text(), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE prompt_versions
            SET content = system_content
            WHERE content IS NULL;
            """
        )
    )
    op.drop_column("prompt_versions", "user_template")
    op.drop_column("prompt_versions", "system_content")
