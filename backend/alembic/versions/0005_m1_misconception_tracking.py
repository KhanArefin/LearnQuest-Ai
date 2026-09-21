"""M1: misconception decay tracking on topic_mastery.

Adds the two fields that drive active -> fading -> cleared in
app/services/mastery.py. The misconception text itself already existed.

NOTE FOR M2: this is revision 0005. Your quiz/progress migration should set
down_revision = "0005_m1_misconception_tracking" so the two chain instead of
branching off 0004 (two heads would need an alembic merge).

Revision ID: 0005_m1_misconception_tracking
Revises: 0004_m1_roadmap_schema
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_m1_misconception_tracking"
down_revision: Union[str, None] = "0004_m1_roadmap_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "topic_mastery",
        sa.Column(
            "misconception_correct_streak",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "topic_mastery",
        sa.Column("misconception_cleared_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("topic_mastery", "misconception_cleared_at")
    op.drop_column("topic_mastery", "misconception_correct_streak")
