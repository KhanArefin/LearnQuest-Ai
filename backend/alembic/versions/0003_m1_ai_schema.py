"""m1: ai schema for conversations, messages, topic_mastery, review_items, recommendations

Revision ID: 0003_m1_ai_schema
Revises: 0002_m4_gamification_schema
Create Date: 2026-09-12 10:25:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003_m1_ai_schema"
down_revision: Union[str, None] = "0002_m4_gamification_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    json_type = postgresql.JSONB(astext_type=sa.Text()) if is_postgres else sa.JSON()

    # --- conversations table ---
    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False, server_default="New conversation"),
        sa.Column("context_lesson_id", sa.Uuid(), sa.ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True),
        sa.Column("context_course_id", sa.Uuid(), sa.ForeignKey("courses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_index("ix_conversations_context_lesson_id", "conversations", ["context_lesson_id"])
    op.create_index("ix_conversations_context_course_id", "conversations", ["context_course_id"])

    # --- messages table ---
    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("audio_url", sa.String(length=500), nullable=True),
        sa.Column("visemes", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])

    # --- topic_mastery table ---
    op.create_table(
        "topic_mastery",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic_tag", sa.String(length=100), nullable=False),
        sa.Column("mastery_score", sa.Numeric(precision=4, scale=3), nullable=False, server_default="0.500"),
        sa.Column("misconception", sa.Text(), nullable=True),
        sa.Column("misconception_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_practiced_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "topic_tag", name="uq_topic_mastery_user_topic"),
    )
    op.create_index("ix_topic_mastery_user_id", "topic_mastery", ["user_id"])
    op.create_index("ix_topic_mastery_topic_tag", "topic_mastery", ["topic_tag"])

    # --- review_items table ---
    op.create_table(
        "review_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic_tag", sa.String(length=100), nullable=False),
        sa.Column("source_lesson_id", sa.Uuid(), sa.ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("interval_days", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "topic_tag", "source_lesson_id", name="uq_review_items_user_topic_lesson"),
    )
    op.create_index("ix_review_items_user_id", "review_items", ["user_id"])
    op.create_index("ix_review_items_due_at", "review_items", ["due_at"])

    # --- recommendations table ---
    op.create_table(
        "recommendations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("score", sa.Numeric(precision=4, scale=3), nullable=False, server_default="0.500"),
        sa.Column("is_dismissed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recommendations_user_id", "recommendations", ["user_id"])


def downgrade() -> None:
    op.drop_table("recommendations")
    op.drop_table("review_items")
    op.drop_table("topic_mastery")
    op.drop_table("messages")
    op.drop_table("conversations")
