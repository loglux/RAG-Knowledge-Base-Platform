"""add admin_invites table

Revision ID: 4fff0bc2e365
Revises: 4f2b8e91a3c7
Create Date: 2026-10-20 23:31:47.327032

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4fff0bc2e365"
down_revision: Union[str, None] = "4f2b8e91a3c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration."""
    op.create_table(
        "admin_invites",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "token_hash", sa.String(length=64), nullable=False, comment="SHA256 hash of the token"
        ),
        sa.Column(
            "label",
            sa.String(length=120),
            nullable=True,
            comment="Optional note, e.g. who this invite is for",
        ),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column(
            "used_by_admin_id",
            sa.Integer(),
            nullable=True,
            comment="Admin account created when this invite was accepted",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["admin_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["used_by_admin_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_admin_invites_created_by"), "admin_invites", ["created_by"], unique=False
    )
    op.create_index(
        op.f("ix_admin_invites_token_hash"), "admin_invites", ["token_hash"], unique=True
    )


def downgrade() -> None:
    """Revert migration."""
    op.drop_index(op.f("ix_admin_invites_token_hash"), table_name="admin_invites")
    op.drop_index(op.f("ix_admin_invites_created_by"), table_name="admin_invites")
    op.drop_table("admin_invites")
