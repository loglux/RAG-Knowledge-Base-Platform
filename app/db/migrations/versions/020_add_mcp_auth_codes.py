"""Add MCP auth codes

Revision ID: 020
Revises: 019
Create Date: 2026-02-12 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mcp_auth_codes",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("admin_user_id", sa.Integer, sa.ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", sa.String(length=255), nullable=False),
        sa.Column("redirect_uri", sa.String(length=2048), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("code_challenge", sa.String(length=255), nullable=False),
        sa.Column("code_challenge_method", sa.String(length=16), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_mcp_auth_codes_admin_user_id", "mcp_auth_codes", ["admin_user_id"])
    op.create_index("ix_mcp_auth_codes_client_id", "mcp_auth_codes", ["client_id"])
    op.create_index("ix_mcp_auth_codes_code_hash", "mcp_auth_codes", ["code_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_mcp_auth_codes_code_hash", table_name="mcp_auth_codes")
    op.drop_index("ix_mcp_auth_codes_client_id", table_name="mcp_auth_codes")
    op.drop_index("ix_mcp_auth_codes_admin_user_id", table_name="mcp_auth_codes")
    op.drop_table("mcp_auth_codes")
