"""AI-generated learning roadmaps: a per-student quest graph.

OWNER: Member 1 (AI Avatar Tutor & Intelligent Learning).

Unlike a fixed skill tree, a roadmap is generated for one student from their
stated goal and their current topic mastery, and can be re-planned when they
struggle. Nodes form a DAG via `depends_on`.

Design note: only *completion* is stored. Whether a node is locked or available
is derived from whether its dependencies are complete (see
`app.services.roadmap_planner.decorate_nodes`). Storing derived state would let
it drift out of sync the moment a node is added, removed or re-planned.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base

JSON_VARIANT = JSONB().with_variant(JSON, "sqlite")


class Roadmap(Base):
    """One student's active plan toward a stated goal."""

    __tablename__ = "roadmaps"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    horizon_weeks: Mapped[int] = mapped_column(Integer, nullable=False, default=8)

    # "active" | "archived" - a student keeps one active roadmap at a time.
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", index=True
    )
    # "llm" | "fallback" - surfaced in the UI so a deterministic plan is never
    # passed off as an AI-generated one.
    generated_by: Mapped[str] = mapped_column(String(20), nullable=False, default="llm")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    nodes: Mapped[list[RoadmapNode]] = relationship(
        "RoadmapNode",
        back_populates="roadmap",
        cascade="all, delete-orphan",
        order_by="RoadmapNode.order_index",
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "goal": self.goal,
            "horizon_weeks": self.horizon_weeks,
            "status": self.status,
            "generated_by": self.generated_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RoadmapNode(Base):
    """A single quest in the roadmap graph."""

    __tablename__ = "roadmap_nodes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    roadmap_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("roadmaps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Stable slug used for dependency edges. The planner emits keys rather than
    # UUIDs so a generated plan can reference nodes before they are persisted.
    node_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Always drawn from the controlled vocabulary (plan.md 3.1) so mastery
    # lookups and lesson matching actually line up.
    topic_tag: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    depends_on: Mapped[list[str]] = mapped_column(
        JSON_VARIANT, nullable=False, default=list
    )

    # The real lesson this quest sends the student to, when one covers the tag.
    lesson_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("lessons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    xp_reward: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=20)

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    roadmap: Mapped[Roadmap] = relationship("Roadmap", back_populates="nodes")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "node_key": self.node_key,
            "title": self.title,
            "summary": self.summary,
            "topic_tag": self.topic_tag,
            "order_index": self.order_index,
            "depends_on": list(self.depends_on or []),
            "lesson_id": str(self.lesson_id) if self.lesson_id else None,
            "xp_reward": self.xp_reward,
            "estimated_minutes": self.estimated_minutes,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "is_completed": self.completed_at is not None,
        }
