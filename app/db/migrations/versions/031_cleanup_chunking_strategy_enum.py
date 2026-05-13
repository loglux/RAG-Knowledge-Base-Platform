"""Drop legacy chunking strategy enum values.

Revision ID: 031
Revises: 030
Create Date: 2026-05-13

History:
- 001_initial_schema created the enum with ('FIXED_SIZE', 'SEMANTIC', 'PARAGRAPH').
- 0f3b9f7a1c9a added ('simple', 'smart', 'semantic') via ALTER TYPE ADD VALUE.
- The application has been writing only the lowercase values since.

This migration consolidates the enum to the three canonical values
('simple', 'smart', 'semantic') by recreating the type. Any rows still
holding legacy labels are remapped: FIXED_SIZE→simple, PARAGRAPH→smart,
SEMANTIC→semantic.
"""

from alembic import op

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Recreate chunkingstrategy enum with only canonical values."""
    op.execute("ALTER TYPE chunkingstrategy RENAME TO chunkingstrategy_old")
    op.execute("CREATE TYPE chunkingstrategy AS ENUM ('simple', 'smart', 'semantic')")
    op.execute("ALTER TABLE knowledge_bases ALTER COLUMN chunking_strategy DROP DEFAULT")
    op.execute("""
        ALTER TABLE knowledge_bases
        ALTER COLUMN chunking_strategy TYPE chunkingstrategy
        USING (
            CASE chunking_strategy::text
                WHEN 'FIXED_SIZE' THEN 'simple'::chunkingstrategy
                WHEN 'PARAGRAPH' THEN 'smart'::chunkingstrategy
                WHEN 'SEMANTIC'   THEN 'semantic'::chunkingstrategy
                ELSE chunking_strategy::text::chunkingstrategy
            END
        )
        """)
    op.execute("ALTER TABLE knowledge_bases ALTER COLUMN chunking_strategy SET DEFAULT 'smart'")
    op.execute("DROP TYPE chunkingstrategy_old")


def downgrade() -> None:
    """Restore the pre-cleanup enum that also carried legacy labels.

    No data is rewritten — anything that was canonical before this
    migration ran is still canonical after the downgrade.
    """
    op.execute("ALTER TYPE chunkingstrategy RENAME TO chunkingstrategy_old")
    op.execute(
        "CREATE TYPE chunkingstrategy AS ENUM "
        "('FIXED_SIZE', 'SEMANTIC', 'PARAGRAPH', 'simple', 'smart', 'semantic')"
    )
    op.execute("ALTER TABLE knowledge_bases ALTER COLUMN chunking_strategy DROP DEFAULT")
    op.execute(
        "ALTER TABLE knowledge_bases "
        "ALTER COLUMN chunking_strategy TYPE chunkingstrategy "
        "USING chunking_strategy::text::chunkingstrategy"
    )
    op.execute(
        "ALTER TABLE knowledge_bases ALTER COLUMN chunking_strategy SET DEFAULT 'FIXED_SIZE'"
    )
    op.execute("DROP TYPE chunkingstrategy_old")
