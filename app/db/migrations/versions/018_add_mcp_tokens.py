"""Add MCP tokens table."""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mcp_tokens",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "admin_user_id",
            sa.Integer,
            sa.ForeignKey("admin_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("token_prefix", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_mcp_tokens_admin_user_id", "mcp_tokens", ["admin_user_id"])
    op.create_index("ix_mcp_tokens_token_hash", "mcp_tokens", ["token_hash"], unique=True)
    op.create_index("ix_mcp_tokens_token_prefix", "mcp_tokens", ["token_prefix"])


def downgrade() -> None:
    op.drop_index("ix_mcp_tokens_token_prefix", table_name="mcp_tokens")
    op.drop_index("ix_mcp_tokens_token_hash", table_name="mcp_tokens")
    op.drop_index("ix_mcp_tokens_admin_user_id", table_name="mcp_tokens")
    op.drop_table("mcp_tokens")
