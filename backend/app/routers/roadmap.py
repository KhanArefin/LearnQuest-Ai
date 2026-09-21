"""AI-generated learning roadmaps (quest graph).

OWNER: Member 1 (AI Avatar Tutor & Intelligent Learning).

A roadmap is planned for one student from their goal plus current mastery, and
can be re-planned as they progress. See app/services/roadmap_planner.py for how
generation is grounded in the real lesson catalogue.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import CurrentUser
from app.models.roadmap import Roadmap, RoadmapNode
from app.services.events import emit
from app.services.roadmap_planner import (
    build_catalogue,
    decorate_nodes,
    generate_steps,
)

logger = logging.getLogger("learnquest.roadmap")

router = APIRouter(prefix="/api/roadmap", tags=["roadmap"])


class GenerateRoadmapRequest(BaseModel):
    goal: str = Field(..., min_length=3, max_length=500)
    horizon_weeks: int = Field(default=8, ge=1, le=52)


def _user_uuid(user: Any) -> uuid.UUID:
    raw = user.get("id") if isinstance(user, dict) else getattr(user, "id", None)
    try:
        return uuid.UUID(str(raw))
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user."
        ) from exc


def _require_db(db: Session | None) -> Session:
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured.",
        )
    return db


def _serialise(roadmap: Roadmap) -> dict[str, Any]:
    nodes = decorate_nodes(roadmap.nodes)
    completed = sum(1 for n in nodes if n["status"] == "completed")
    earned = sum(n["xp_reward"] for n in nodes if n["status"] == "completed")

    return {
        **roadmap.to_dict(),
        "nodes": nodes,
        "progress": {
            "total": len(nodes),
            "completed": completed,
            "percent": round(completed / len(nodes) * 100) if nodes else 0,
            "xp_earned": earned,
            "xp_available": sum(n["xp_reward"] for n in nodes),
            # What the student should do next - the UI leads with this.
            "next_node_key": next(
                (n["node_key"] for n in nodes if n["status"] == "available"), None
            ),
        },
    }


@router.get("/me")
def my_roadmap(user: CurrentUser, db: Session | None = Depends(get_db)) -> dict[str, Any]:
    """The student's active roadmap, or {roadmap: None} if they have none yet."""
    database = _require_db(db)
    user_id = _user_uuid(user)

    roadmap = (
        database.query(Roadmap)
        .filter(Roadmap.user_id == user_id, Roadmap.status == "active")
        .order_by(Roadmap.created_at.desc())
        .first()
    )
    if not roadmap:
        return {"roadmap": None}
    return {"roadmap": _serialise(roadmap)}


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_roadmap(
    body: GenerateRoadmapRequest,
    user: CurrentUser,
    db: Session | None = Depends(get_db),
) -> dict[str, Any]:
    """Plan a roadmap for a goal, archiving any previous active one."""
    database = _require_db(db)
    user_id = _user_uuid(user)

    steps, generated_by, catalogue = await generate_steps(
        database, user_id, body.goal, body.horizon_weeks
    )
    if not steps:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "No published lessons are available to build a roadmap from. "
                "Seed the catalogue first."
            ),
        )

    # One active roadmap per student; keep the old one for history.
    (
        database.query(Roadmap)
        .filter(Roadmap.user_id == user_id, Roadmap.status == "active")
        .update({"status": "archived"}, synchronize_session=False)
    )

    roadmap = Roadmap(
        user_id=user_id,
        goal=body.goal.strip(),
        horizon_weeks=body.horizon_weeks,
        status="active",
        generated_by=generated_by,
    )
    database.add(roadmap)
    database.flush()  # assign roadmap.id before attaching nodes

    for index, step in enumerate(steps, start=1):
        entry = catalogue.get(step["tag"], {})
        minutes = int(entry.get("minutes") or 20)
        database.add(
            RoadmapNode(
                roadmap_id=roadmap.id,
                node_key=step["key"],
                title=step["title"],
                summary=step["summary"],
                topic_tag=step["tag"],
                order_index=index,
                depends_on=step["depends_on"],
                lesson_id=entry.get("lesson_id"),
                # Longer quests are worth more, rounded to a tidy number.
                xp_reward=max(25, round(minutes * 2 / 5) * 5),
                estimated_minutes=minutes,
            )
        )

    database.commit()
    database.refresh(roadmap)

    logger.info(
        "Roadmap generated user=%s steps=%d via=%s", user_id, len(steps), generated_by
    )
    return {"roadmap": _serialise(roadmap)}


@router.post("/nodes/{node_id}/complete")
def complete_node(
    node_id: uuid.UUID,
    user: CurrentUser,
    db: Session | None = Depends(get_db),
) -> dict[str, Any]:
    """Mark a quest complete and award its XP."""
    database = _require_db(db)
    user_id = _user_uuid(user)

    node = (
        database.query(RoadmapNode)
        .join(Roadmap, RoadmapNode.roadmap_id == Roadmap.id)
        .filter(RoadmapNode.id == node_id, Roadmap.user_id == user_id)
        .first()
    )
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Quest not found."
        )

    roadmap = node.roadmap

    # Refuse to complete a node whose prerequisites are unmet, so the graph
    # cannot be short-circuited by calling the API directly.
    done = {n.node_key for n in roadmap.nodes if n.completed_at is not None}
    blocked = [d for d in (node.depends_on or []) if d not in done]
    if blocked and node.completed_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Finish these first: {', '.join(blocked)}",
        )

    awarded = 0
    if node.completed_at is None:  # idempotent: never double-award XP
        node.completed_at = datetime.now(timezone.utc)
        awarded = node.xp_reward
        database.commit()

        try:
            emit(
                database,
                user_id,
                "roadmap.node_completed",
                {
                    "node_id": str(node.id),
                    "topic_tag": node.topic_tag,
                    "xp": awarded,
                },
            )
        except Exception as exc:  # noqa: BLE001 - XP side effects must not 500
            logger.warning("roadmap.node_completed event failed: %s", exc)

    database.refresh(roadmap)
    return {"xp_awarded": awarded, "roadmap": _serialise(roadmap)}


@router.post("/replan")
async def replan_roadmap(
    user: CurrentUser,
    db: Session | None = Depends(get_db),
) -> dict[str, Any]:
    """Re-plan the remaining path against the student's updated mastery.

    Completed quests are preserved: the student keeps their progress and XP,
    and only the road ahead is redrawn.
    """
    database = _require_db(db)
    user_id = _user_uuid(user)

    current = (
        database.query(Roadmap)
        .filter(Roadmap.user_id == user_id, Roadmap.status == "active")
        .order_by(Roadmap.created_at.desc())
        .first()
    )
    if not current:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active roadmap to re-plan.",
        )

    finished = [n for n in current.nodes if n.completed_at is not None]
    finished_tags = {n.topic_tag for n in finished}

    steps, generated_by, catalogue = await generate_steps(
        database, user_id, current.goal, current.horizon_weeks
    )
    # Anything already done stays done - do not re-issue it as a new quest.
    steps = [s for s in steps if s["tag"] not in finished_tags]

    # Drop only the unfinished nodes, then append the new plan after them.
    for node in list(current.nodes):
        if node.completed_at is None:
            database.delete(node)
    database.flush()

    done_keys = [n.node_key for n in finished]
    offset = len(finished)
    for index, step in enumerate(steps, start=1):
        entry = catalogue.get(step["tag"], {})
        minutes = int(entry.get("minutes") or 20)
        # The first new quest hangs off everything already completed, so the
        # graph stays connected after surgery.
        depends = step["depends_on"] or (done_keys[-1:] if index == 1 else [])
        database.add(
            RoadmapNode(
                roadmap_id=current.id,
                node_key=step["key"],
                title=step["title"],
                summary=step["summary"],
                topic_tag=step["tag"],
                order_index=offset + index,
                depends_on=depends,
                lesson_id=entry.get("lesson_id"),
                xp_reward=max(25, round(minutes * 2 / 5) * 5),
                estimated_minutes=minutes,
            )
        )

    current.generated_by = generated_by
    database.commit()
    database.refresh(current)

    logger.info("Roadmap re-planned user=%s new_steps=%d", user_id, len(steps))
    return {"roadmap": _serialise(current)}
