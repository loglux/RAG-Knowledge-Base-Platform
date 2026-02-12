"""Add MCP auth events

Revision ID: 021
Revises: 020
Create Date: 2026-02-12 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mcp_auth_events",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("admin_user_id", sa.Integer, sa.ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("client_id", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_mcp_auth_events_admin_user_id", "mcp_auth_events", ["admin_user_id"])
    op.create_index("ix_mcp_auth_events_client_id", "mcp_auth_events", ["client_id"])
    op.create_index("ix_mcp_auth_events_event_type", "mcp_auth_events", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_mcp_auth_events_event_type", table_name="mcp_auth_events")
    op.drop_index("ix_mcp_auth_events_client_id", table_name="mcp_auth_events")
    op.drop_index("ix_mcp_auth_events_admin_user_id", table_name="mcp_auth_events")
    op.drop_table("mcp_auth_events")
