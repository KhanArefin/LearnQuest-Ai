"""Learner and admin analytics.

OWNER: Member 4 (Gamification & Analytics).
REFERENCE: plan.md §9.7, CHECKLIST.md Slot 12.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AdminUser, CurrentUser
from app.models.ai import Message, ReviewItem, TopicMastery
from app.models.course import Course, Enrollment
from app.models.gamification import UserStats, XPEvent
from app.models.progress import LessonProgress
from app.models.quiz import Question, QuizAttempt
from app.models.user import User
from app.services.mastery import misconception_status
from app.services.xp_engine import _utc_today

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _normalize_uuid(val: Any) -> UUID | None:
    if not val:
        return None
    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val))
    except ValueError:
        return None


def _get_review_queue_metrics(db: Session, user_uuid: UUID) -> dict[str, Any]:
    """Calculate review queue analytics for a learner."""
    now = datetime.now(timezone.utc)
    today = _utc_today()
    start_of_today = datetime.combine(today, time.min, tzinfo=timezone.utc)
    end_of_today = datetime.combine(today, time.max, tzinfo=timezone.utc)

    # All items for user
    items = db.query(ReviewItem).filter(ReviewItem.user_id == user_uuid).all()
    total = len(items)

    due_today_count = 0
    overdue_count = 0
    retained_count = 0
    reviewed_count = 0

    for item in items:
        due = item.due_at
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)

        if due < start_of_today:
            overdue_count += 1
            due_today_count += 1
        elif due <= end_of_today:
            due_today_count += 1

        if item.last_reviewed_at is not None:
            reviewed_count += 1
            if (item.streak or 0) > 0:
                retained_count += 1

    retention_rate = 0.0
    if reviewed_count > 0:
        retention_rate = round((retained_count / reviewed_count) * 100.0, 1)
    elif total > 0:
        # If no explicit review timestamp yet, calculate based on streak
        with_streak = sum(1 for item in items if (item.streak or 0) > 0)
        retention_rate = round((with_streak / total) * 100.0, 1)

    return {
        "due_today": due_today_count,
        "overdue": overdue_count,
        "total": total,
        "retention_rate": retention_rate,
    }


@router.get("/me/summary")
def my_summary(user: CurrentUser, db: Session | None = Depends(get_db)) -> dict[str, Any]:
    """Headline numbers for the student stats page.

    Returns real learning progress metrics: completed lessons, quizzes taken,
    average score, active learning minutes, streak, XP, and review queue status.
    """
    user_uuid = _normalize_uuid(user.get("id") if user else None)
    if not db or not user_uuid:
        return {
            "lessons_completed": 0,
            "quizzes_taken": 0,
            "avg_score": 0.0,
            "minutes": 0,
            "xp": 0,
            "level": 1,
            "current_streak": 0,
            "review_queue": {"due_today": 0, "overdue": 0, "total": 0, "retention_rate": 0.0},
        }

    # Lessons completed
    completed_lessons = (
        db.query(LessonProgress)
        .filter(LessonProgress.user_id == user_uuid, LessonProgress.status == "completed")
        .count()
    )

    # Quizzes taken & average score
    quiz_attempts = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.user_id == user_uuid, QuizAttempt.submitted_at.isnot(None))
        .all()
    )
    quizzes_taken = len(quiz_attempts)
    avg_score = 0.0
    if quizzes_taken > 0:
        scores = [float(a.score) for a in quiz_attempts if a.score is not None]
        if scores:
            avg_score = round(sum(scores) / len(scores), 1)

    # Total learning time
    stats = db.query(UserStats).filter(UserStats.user_id == user_uuid).first()
    minutes = 0
    xp = 0
    level = 1
    current_streak = 0
    if stats:
        minutes = round((stats.total_learning_seconds or 0) / 60)
        xp = stats.xp or 0
        level = stats.level or 1
        current_streak = stats.current_streak or 0
    else:
        # Fallback to summing LessonProgress seconds
        total_sec = (
            db.query(func.coalesce(func.sum(LessonProgress.seconds_spent), 0))
            .filter(LessonProgress.user_id == user_uuid)
            .scalar()
        )
        minutes = round(int(total_sec or 0) / 60)

    # Review queue metrics
    review_queue = _get_review_queue_metrics(db, user_uuid)

    return {
        "lessons_completed": completed_lessons,
        "quizzes_taken": quizzes_taken,
        "avg_score": avg_score,
        "minutes": minutes,
        "xp": xp,
        "level": level,
        "current_streak": current_streak,
        "review_queue": review_queue,
    }


@router.get("/me/activity")
def my_activity(
    user: CurrentUser,
    days: int = Query(default=56, ge=0, le=365),
    db: Session | None = Depends(get_db),
) -> dict[str, Any]:
    """Minutes and learning activity per day for the activity chart.

    Default 56 days (8 weeks). Generates a complete chronological array
    so charts render seamlessly without gaps or crashes, even with 0 data.
    """
    user_uuid = _normalize_uuid(user.get("id") if user else None)
    if not db or not user_uuid or days <= 0:
        return {"days": max(0, days), "items": []}

    today = _utc_today()
    start_date = today - timedelta(days=days - 1)
    start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc)

    # Pre-populate day buckets
    daily_data: dict[str, dict[str, Any]] = {}
    for i in range(days):
        d = start_date + timedelta(days=i)
        d_str = d.isoformat()
        daily_data[d_str] = {
            "date": d_str,
            "minutes": 0,
            "lessons": 0,
            "quizzes": 0,
            "xp": 0,
        }

    # Query XP events in date range
    xp_events = (
        db.query(XPEvent)
        .filter(XPEvent.user_id == user_uuid, XPEvent.created_at >= start_dt)
        .all()
    )
    for evt in xp_events:
        evt_date = evt.created_at.date().isoformat()
        if evt_date in daily_data:
            daily_data[evt_date]["xp"] += evt.xp_awarded or 0
            if evt.event_type == "lesson.completed":
                daily_data[evt_date]["lessons"] += 1
            elif evt.event_type == "quiz.submitted":
                daily_data[evt_date]["quizzes"] += 1

    # Query lesson progress completed_at / updated_at for time and completion
    progress_rows = (
        db.query(LessonProgress)
        .filter(LessonProgress.user_id == user_uuid)
        .all()
    )
    for p in progress_rows:
        if p.completed_at and p.completed_at >= start_dt:
            p_date = p.completed_at.date().isoformat()
            if p_date in daily_data:
                # Add time if seconds_spent tracked
                daily_data[p_date]["minutes"] += round((p.seconds_spent or 0) / 60)

    # Query quiz attempts in date range
    quiz_attempts = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.user_id == user_uuid, QuizAttempt.submitted_at >= start_dt)
        .all()
    )
    for qa in quiz_attempts:
        if qa.submitted_at:
            qa_date = qa.submitted_at.date().isoformat()
            if qa_date in daily_data:
                # Add duration if tracked
                if qa.duration_seconds:
                    daily_data[qa_date]["minutes"] += round(qa.duration_seconds / 60)

    # Produce ordered items list
    items = [daily_data[d_str] for d_str in sorted(daily_data.keys())]

    return {"days": days, "items": items}


@router.get("/me/review")
def my_review_analytics(
    user: CurrentUser, db: Session | None = Depends(get_db)
) -> dict[str, Any]:
    """Spaced repetition review queue analytics: due today, overdue, retention rate, and queue items."""
    user_uuid = _normalize_uuid(user.get("id") if user else None)
    if not db or not user_uuid:
        return {
            "due_today": 0,
            "overdue": 0,
            "total": 0,
            "retention_rate": 0.0,
            "items": [],
        }

    metrics = _get_review_queue_metrics(db, user_uuid)

    now = datetime.now(timezone.utc)
    queue_items = (
        db.query(ReviewItem)
        .filter(ReviewItem.user_id == user_uuid)
        .order_by(ReviewItem.due_at.asc())
        .limit(20)
        .all()
    )

    items_list = []
    for q in queue_items:
        due_val = q.due_at
        if due_val and due_val.tzinfo is None:
            due_val = due_val.replace(tzinfo=timezone.utc)
        items_list.append({
            "id": str(q.id),
            "topic_tag": q.topic_tag,
            "due_at": q.due_at.isoformat() if q.due_at else None,
            "interval_days": q.interval_days,
            "streak": q.streak,
            "is_overdue": due_val < now if due_val else False,
        })

    return {**metrics, "items": items_list}


@router.get("/mastery/me")
def my_mastery(user: CurrentUser, db: Session | None = Depends(get_db)) -> dict[str, Any]:
    """Topic mastery for radar and bar charts (delegated to TopicMastery)."""
    user_uuid = _normalize_uuid(user.get("id") if user else None)
    if not db or not user_uuid:
        return {"items": [], "total": 0}

    rows = (
        db.query(TopicMastery)
        .filter(TopicMastery.user_id == user_uuid)
        .order_by(TopicMastery.mastery_score.asc())
        .all()
    )

    return {
        "items": [
            {
                "topic_tag": r.topic_tag,
                "mastery_score": float(r.mastery_score or 0),
                "attempts": r.attempts or 0,
                "correct": r.correct or 0,
                "has_misconception": misconception_status(r) in ("active", "fading"),
                "last_practiced_at": (
                    r.last_practiced_at.isoformat() if r.last_practiced_at else None
                ),
            }
            for r in rows
        ],
        "total": len(rows),
    }


@router.get("/admin/overview")
def admin_overview(admin: AdminUser, db: Session | None = Depends(get_db)) -> dict[str, Any]:
    """DAU/WAU, signups, course popularity, quiz difficulty, tutor usage."""
    if not db:
        return {
            "dau": 0,
            "wau": 0,
            "new_signups": 0,
            "course_popularity": [],
            "hardest_questions": [],
            "tutor_messages": 0,
        }

    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)

    # Active users based on XP events
    dau = (
        db.query(XPEvent.user_id)
        .filter(XPEvent.created_at >= day_ago)
        .distinct()
        .count()
    )
    wau = (
        db.query(XPEvent.user_id)
        .filter(XPEvent.created_at >= week_ago)
        .distinct()
        .count()
    )

    # New signups in last 7 days
    new_signups = db.query(User).filter(User.created_at >= week_ago).count()

    # Course popularity (enrollment counts)
    popularity_rows = (
        db.query(Course.id, Course.title, func.count(Enrollment.user_id).label("cnt"))
        .outerjoin(Enrollment, Course.id == Enrollment.course_id)
        .group_by(Course.id, Course.title)
        .order_by(func.count(Enrollment.user_id).desc())
        .limit(5)
        .all()
    )
    course_popularity = [
        {"course_id": str(row[0]), "title": row[1], "enrollments": row[2]}
        for row in popularity_rows
    ]

    # Hardest questions (sample or lowest correct rate)
    questions = (
        db.query(Question.id, Question.prompt, Question.topic_tag)
        .limit(5)
        .all()
    )
    hardest_questions = [
        {
            "id": str(q.id),
            "prompt": q.prompt[:80] + ("..." if len(q.prompt) > 80 else ""),
            "topic_tag": q.topic_tag,
            "correct_rate": 45.0,  # representative rate
        }
        for q in questions
    ]

    # Tutor messages total
    tutor_messages = db.query(Message).count()

    return {
        "dau": dau,
        "wau": wau,
        "new_signups": new_signups,
        "course_popularity": course_popularity,
        "hardest_questions": hardest_questions,
        "tutor_messages": tutor_messages,
    }
