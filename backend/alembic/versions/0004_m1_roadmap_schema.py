"""M1 roadmap schema: AI-generated learning roadmaps and their quest nodes.

Revision ID: 0004_m1_roadmap_schema
Revises: 0003_m1_ai_schema
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004_m1_roadmap_schema"
down_revision: Union[str, None] = "0003_m1_ai_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# JSONB on Postgres, JSON on SQLite - matches app/models/roadmap.py.
JSON_VARIANT = postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "roadmaps",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("horizon_weeks", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("generated_by", sa.String(length=20), nullable=False, server_default="llm"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_roadmaps_user_id", "roadmaps", ["user_id"])
    op.create_index("ix_roadmaps_status", "roadmaps", ["status"])

    op.create_table(
        "roadmap_nodes",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "roadmap_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("roadmaps.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("node_key", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("topic_tag", sa.String(length=100), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("depends_on", JSON_VARIANT, nullable=False, server_default="[]"),
        sa.Column(
            "lesson_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("lessons.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("xp_reward", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_roadmap_nodes_roadmap_id", "roadmap_nodes", ["roadmap_id"])
    op.create_index("ix_roadmap_nodes_node_key", "roadmap_nodes", ["node_key"])
    op.create_index("ix_roadmap_nodes_topic_tag", "roadmap_nodes", ["topic_tag"])
    op.create_index("ix_roadmap_nodes_lesson_id", "roadmap_nodes", ["lesson_id"])


def downgrade() -> None:
    op.drop_index("ix_roadmap_nodes_lesson_id", table_name="roadmap_nodes")
    op.drop_index("ix_roadmap_nodes_topic_tag", table_name="roadmap_nodes")
    op.drop_index("ix_roadmap_nodes_node_key", table_name="roadmap_nodes")
    op.drop_index("ix_roadmap_nodes_roadmap_id", table_name="roadmap_nodes")
    op.drop_table("roadmap_nodes")

    op.drop_index("ix_roadmaps_status", table_name="roadmaps")
    op.drop_index("ix_roadmaps_user_id", table_name="roadmaps")
    op.drop_table("roadmaps")
