"""add retrieval_settings_json to knowledge_bases

Revision ID: f9c1a2b3c4d5
Revises: f4a5b6c7d8e9
Create Date: 2026-02-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f9c1a2b3c4d5"
down_revision: Union[str, None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("knowledge_bases", sa.Column("retrieval_settings_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("knowledge_bases", "retrieval_settings_json")
