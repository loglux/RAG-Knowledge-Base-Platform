"""Add feedback (thumbs rating + comment) to chat messages.

Closes the chat ↔ eval loop foundation: every assistant message can be
rated by the viewer, so real-world successful Q&A pairs can later be
promoted into the qa_eval gold corpus and bad ones flagged for review.

The rating is stored on the message itself rather than in a separate
table because in the current MVP there is no per-user data — each
conversation has one effective rater. When multi-user auth lands, this
can move to a join table without changing the API surface.

Revision ID: 033
Revises: 032
Create Date: 2026-05-16
"""

import sqlalchemy as sa
from alembic import op

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_messages",
        sa.Column(
            "rating",
            sa.SmallInteger(),
            nullable=False,
            server_default="0",
            comment="-1 = thumbs down, 0 = no rating, +1 = thumbs up",
        ),
    )
    op.add_column(
        "chat_messages",
        sa.Column(
            "rating_comment",
            sa.Text(),
            nullable=True,
            comment="Optional free-text feedback attached to the rating",
        ),
    )


def downgrade() -> None:
    op.drop_column("chat_messages", "rating_comment")
    op.drop_column("chat_messages", "rating")
