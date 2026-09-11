"""Lesson content and delivery.

OWNER: Member 2. See plan.md §7.3.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.database import database_is_configured, get_db
from app.deps import CurrentUser
from app.models.course import Course, Lesson
from app.services.events import emit

logger = logging.getLogger("learnquest.lessons")

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


@router.get("/{lesson_id}", response_model=dict[str, Any])
def get_lesson(
    lesson_id: str,
    user: CurrentUser,
    db: Session | None = Depends(get_db),
) -> dict[str, Any]:
    """Lesson markdown, video, tags and sibling navigation."""
    if not db or not database_is_configured():
        return {
            "id": lesson_id,
            "title": "Demo Lesson",
            "content_md": "# Demo Lesson\n\nDatabase not connected.",
            "topic_tags": [],
            "estimated_minutes": 10,
            "order_index": 1,
        }

    try:
        l_uuid = uuid.UUID(lesson_id)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid lesson ID.",
        ) from err

    lesson = (
        db.query(Lesson)
        .options(joinedload(Lesson.course).joinedload(Course.lessons))
        .filter(Lesson.id == l_uuid)
        .first()
    )

    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lesson '{lesson_id}' not found.",
        )

    data = lesson.to_dict()

    if lesson.course:
        sorted_lessons = sorted(lesson.course.lessons, key=lambda l: l.order_index)
        data["course"] = {
            "id": str(lesson.course.id),
            "title": lesson.course.title,
            "slug": lesson.course.slug,
            "lessons": [
                {
                    "id": str(l.id),
                    "title": l.title,
                    "order_index": l.order_index,
                    "estimated_minutes": l.estimated_minutes,
                }
                for l in sorted_lessons
            ],
        }

        # Calculate previous and next lesson
        idx = next((i for i, l in enumerate(sorted_lessons) if l.id == lesson.id), -1)
        data["prev_lesson"] = (
            {"id": str(sorted_lessons[idx - 1].id), "title": sorted_lessons[idx - 1].title}
            if idx > 0
            else None
        )
        data["next_lesson"] = (
            {"id": str(sorted_lessons[idx + 1].id), "title": sorted_lessons[idx + 1].title}
            if idx >= 0 and idx < len(sorted_lessons) - 1
            else None
        )

    return data


@router.post("/{lesson_id}/progress", response_model=dict[str, Any])
def update_progress(
    lesson_id: str,
    user: CurrentUser,
    payload: dict,
    db: Session | None = Depends(get_db),
) -> dict[str, Any]:
    """Record progress heartbeat or completion. On status=completed, emits lesson.completed."""
    status_val = payload.get("status", "in_progress")
    seconds_spent = payload.get("seconds_spent", 0)
    last_position = payload.get("last_position", 0)

    if db and database_is_configured() and status_val == "completed":
        try:
            u_id = uuid.UUID(user["id"])
            emit(
                db,
                u_id,
                "lesson.completed",
                {
                    "lesson_id": lesson_id,
                    "seconds": seconds_spent,
                },
            )
        except Exception as e:
            logger.warning("Error emitting lesson.completed event: %s", e)

    return {
        "lesson_id": lesson_id,
        "status": status_val,
        "seconds_spent": seconds_spent,
        "last_position": last_position,
    }
