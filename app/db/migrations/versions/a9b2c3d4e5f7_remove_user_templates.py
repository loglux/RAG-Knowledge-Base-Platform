"""Remove user_template columns from prompt tables.

Revision ID: a9b2c3d4e5f7
Revises: a8b1c2d3e4f6
Create Date: 2026-02-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a9b2c3d4e5f7"
down_revision: Union[str, None] = "a8b1c2d3e4f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration."""
    op.drop_column("prompt_versions", "user_template")
    op.drop_column("self_check_prompt_versions", "user_template")


def downgrade() -> None:
    """Revert migration."""
    op.add_column("prompt_versions", sa.Column("user_template", sa.Text(), nullable=True))
    op.add_column(
        "self_check_prompt_versions", sa.Column("user_template", sa.Text(), nullable=True)
    )
