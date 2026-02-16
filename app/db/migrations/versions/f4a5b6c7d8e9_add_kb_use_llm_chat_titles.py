"""add use_llm_chat_titles to knowledge_bases

Revision ID: f4a5b6c7d8e9
Revises: e3f4a1b2c3d4
Create Date: 2026-02-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, None] = "e3f4a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("knowledge_bases", sa.Column("use_llm_chat_titles", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("knowledge_bases", "use_llm_chat_titles")
