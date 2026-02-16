"""Add MCP refresh tokens

Revision ID: 019
Revises: 018
Create Date: 2026-02-11 07:20:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mcp_refresh_tokens",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "admin_user_id",
            sa.Integer,
            sa.ForeignKey("admin_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("jti", sa.String(length=36), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_mcp_refresh_tokens_admin_user_id", "mcp_refresh_tokens", ["admin_user_id"])
    op.create_index("ix_mcp_refresh_tokens_jti", "mcp_refresh_tokens", ["jti"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_mcp_refresh_tokens_jti", table_name="mcp_refresh_tokens")
    op.drop_index("ix_mcp_refresh_tokens_admin_user_id", table_name="mcp_refresh_tokens")
    op.drop_table("mcp_refresh_tokens")
