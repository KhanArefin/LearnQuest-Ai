"""M1: topic vocabulary table + generation jobs.

Two foundations for generating content per student.

`topics` turns the tag vocabulary into data. It was a Python list in
seed_data.py that nothing enforced, which was fine while every tag was written
by hand. Once a model is tagging generated lessons it is not: it will invent
`sql.joins`, `dbms.joins` and `databases.inner_join` for one idea, each becomes
its own topic_mastery row, and the misconception map fragments into noise.

`generation_jobs` exists because generation is slow. Measured: ~8s per
lesson-sized completion, so a course is ~100s, against a 30s client timeout.

Revision ID: 0009_m1_topics_and_jobs
Revises: 0008_m1_conversation_number
"""

from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_m1_topics_and_jobs"
down_revision: Union[str, None] = "0008_m1_conversation_number"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Seeded from TOPIC_VOCABULARY in app/seed/seed_data.py, which stays as the
# source of truth for the demo content itself.
SEED_TOPICS = [
    ("python.basics", "Python basics", "python"),
    ("python.loops", "Loops and iteration", "python"),
    ("python.functions", "Functions", "python"),
    ("python.oop", "Object-oriented programming", "python"),
    ("dbms.er_model", "ER model and keys", "dbms"),
    ("dbms.normalization", "Normalization", "dbms"),
    ("dbms.sql_joins", "SQL joins", "dbms"),
    ("dbms.transactions", "Transactions and ACID", "dbms"),
    ("web.html_css", "HTML and CSS", "web"),
    ("web.javascript", "JavaScript", "web"),
    ("web.react", "React", "web"),
    ("web.rest_api", "REST APIs", "web"),
]


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    json_type = postgresql.JSONB(astext_type=sa.Text()) if is_postgres else sa.JSON()

    topics = op.create_table(
        "topics",
        sa.Column("tag", sa.String(length=100), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("subject", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("tag"),
    )
    op.create_index("ix_topics_subject", "topics", ["subject"])

    # A concrete timestamp, not sa.func.now(): bulk_insert binds these as
    # parameters and the driver cannot adapt a SQL function expression.
    now = datetime.now(timezone.utc)
    op.bulk_insert(
        topics,
        [
            {
                "tag": tag,
                "label": label,
                "subject": subject,
                "is_active": True,
                "created_at": now,
            }
            for tag, label, subject in SEED_TOPICS
        ],
    )

    op.create_table(
        "generation_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("params", json_type, nullable=False),
        sa.Column("result", json_type, nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_generation_jobs_user_id", "generation_jobs", ["user_id"])
    op.create_index("ix_generation_jobs_kind", "generation_jobs", ["kind"])
    op.create_index("ix_generation_jobs_status", "generation_jobs", ["status"])
    op.create_index("ix_generation_jobs_created_at", "generation_jobs", ["created_at"])


def downgrade() -> None:
    op.drop_table("generation_jobs")
    op.drop_index("ix_topics_subject", table_name="topics")
    op.drop_table("topics")
