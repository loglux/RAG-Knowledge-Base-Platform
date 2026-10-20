"""convert user_id columns from UUID to admin_users FK

Revision ID: 4f2b8e91a3c7
Revises: 8a1f3c6d9b02
Create Date: 2026-10-20 20:10:00.000000

knowledge_bases.user_id / documents.user_id / conversations.user_id /
url_crawl_jobs.user_id were all added as nullable UUID columns "for future
use when auth is implemented" - auth (JWT, app/core/auth.py) has been
implemented for a while, but these columns were never wired up and remain
NULL on every row across all three deployments (verified before writing
this migration - 0 non-null values anywhere). AdminUser.id is an int, not a
UUID, so these columns could never have actually referenced it.

This converts them to a real FK on admin_users.id (ON DELETE SET NULL - an
admin account being removed shouldn't cascade-delete their knowledge bases/
documents/conversations, just orphan them back to "accessible to
everyone", same as never having had an owner).

Existing NULL rows are backfilled to admin_users.id = 1 (the first/primary
admin on every one of the three deployments, per project memory) rather
than left NULL - the alternative (leaving them ownerless) would make every
existing knowledge base/document/conversation visible to every admin
forever, defeating the point of adding isolation now. The backfill is
conditional on admin id 1 actually existing, so this is also safe to run
against a brand-new deployment with no admin yet (0 rows to update).

prompt_versions.created_by / self_check_prompt_versions.created_by have the
exact same stale-UUID problem but are a different case: prompts are global
app-wide configuration, not per-user-scoped data (app/api/v1/prompts.py has
no ownership checks and shouldn't - everyone shares the same active
prompt). created_by there is audit-only ("who created this version"), so
those two just get the type fix, no backfill - NULL ("unknown creator") is
a perfectly fine value for an audit field.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4f2b8e91a3c7"
down_revision: Union[str, None] = "8a1f3c6d9b02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OWNERSHIP_TABLES = ("knowledge_bases", "documents", "conversations", "url_crawl_jobs")
_AUDIT_TABLES = ("prompt_versions", "self_check_prompt_versions")


def upgrade() -> None:
    """Apply migration."""
    for table in _OWNERSHIP_TABLES:
        op.drop_column(table, "user_id")
        op.add_column(
            table,
            sa.Column(
                "user_id",
                sa.Integer(),
                nullable=True,
                comment=(
                    "Owner admin user ID - None means accessible to everyone "
                    "(legacy/pre-isolation data)"
                ),
            ),
        )
        op.create_foreign_key(
            f"{table}_user_id_fkey",  # matches Postgres' own default FK naming convention
            table,
            "admin_users",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index(op.f(f"ix_{table}_user_id"), table, ["user_id"], unique=False)

        op.execute(
            f"UPDATE {table} SET user_id = 1 "
            "WHERE user_id IS NULL "
            "AND EXISTS (SELECT 1 FROM admin_users WHERE id = 1)"
        )

    for table in _AUDIT_TABLES:
        op.drop_column(table, "created_by")
        op.add_column(
            table,
            sa.Column(
                "created_by",
                sa.Integer(),
                nullable=True,
                comment="Creator admin user ID (audit only - prompts are global, not per-user scoped)",
            ),
        )
        op.create_foreign_key(
            f"{table}_created_by_fkey",
            table,
            "admin_users",
            ["created_by"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index(op.f(f"ix_{table}_created_by"), table, ["created_by"], unique=False)


def downgrade() -> None:
    """Revert migration."""
    for table in _AUDIT_TABLES:
        op.drop_index(op.f(f"ix_{table}_created_by"), table_name=table)
        op.drop_constraint(f"{table}_created_by_fkey", table, type_="foreignkey")
        op.drop_column(table, "created_by")
        op.add_column(
            table,
            sa.Column(
                "created_by",
                sa.UUID(),
                nullable=True,
                comment="Creator user ID (nullable for MVP)",
            ),
        )

    for table in _OWNERSHIP_TABLES:
        op.drop_index(op.f(f"ix_{table}_user_id"), table_name=table)
        op.drop_constraint(f"{table}_user_id_fkey", table, type_="foreignkey")
        op.drop_column(table, "user_id")
        op.add_column(
            table,
            sa.Column(
                "user_id",
                sa.UUID(),
                nullable=True,
                comment="Owner user ID - nullable for MVP",
            ),
        )
