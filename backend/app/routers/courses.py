"""Course catalog and enrollment.

OWNER: Member 2 (reads) / Member 3 (writes). See plan.md §7.3.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.database import database_is_configured, get_db
from app.deps import CurrentUser
from app.models.course import Course, Enrollment, Lesson
from app.models.quiz import Quiz
from app.schemas.course import CourseDetailResponse, CourseResponse, EnrollmentResponse
from app.services.events import emit

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.get("", response_model=dict[str, Any])
def list_courses(
    search: str | None = None,
    subject: str | None = None,
    difficulty: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session | None = Depends(get_db),
) -> dict[str, Any]:
    """Published courses, filterable. Public - no auth required."""
    if not db or not database_is_configured():
        return {"items": [], "total": 0, "page": page, "page_size": page_size}

    query = db.query(Course).filter(Course.is_published.is_(True))

    if search:
        search_filter = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Course.title.ilike(search_filter),
                Course.description.ilike(search_filter),
                Course.subject.ilike(search_filter),
            )
        )
    if subject:
        query = query.filter(Course.subject.ilike(subject.strip()))
    if difficulty:
        query = query.filter(Course.difficulty.ilike(difficulty.strip()))

    total = query.count()
    courses = (
        query.order_by(Course.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [CourseResponse.model_validate(c.to_dict()).model_dump() for c in courses]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{slug}", response_model=CourseDetailResponse)
def get_course(
    slug: str,
    db: Session | None = Depends(get_db),
) -> dict[str, Any]:
    """Course detail with its ordered lesson list."""
    if not db or not database_is_configured():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found.",
            headers={"X-Error-Code": "COURSE_NOT_FOUND"},
        )

    # Allow lookup by slug or by UUID
    course = None
    try:
        course_uuid = uuid.UUID(slug)
        course = (
            db.query(Course)
            .options(joinedload(Course.lessons))
            .filter(Course.id == course_uuid)
            .first()
        )
    except ValueError:
        pass

    if not course:
        course = (
            db.query(Course)
            .options(joinedload(Course.lessons))
            .filter(Course.slug == slug)
            .first()
        )

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course '{slug}' not found.",
            headers={"X-Error-Code": "COURSE_NOT_FOUND"},
        )

    course_dict = course.to_dict(include_lessons=False)
    lesson_ids = [l.id for l in course.lessons]
    quizzes_by_lesson: dict[uuid.UUID, str] = {}
    if lesson_ids:
        quizzes = db.query(Quiz).filter(Quiz.lesson_id.in_(lesson_ids)).all()
        for q in quizzes:
            if q.lesson_id:
                quizzes_by_lesson[q.lesson_id] = str(q.id)

    sorted_lessons = sorted(course.lessons, key=lambda l: l.order_index)
    lessons_out = []
    for l in sorted_lessons:
        l_dict = l.to_dict()
        l_dict["quiz_id"] = quizzes_by_lesson.get(l.id)
        lessons_out.append(l_dict)
    course_dict["lessons"] = lessons_out

    return course_dict


@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_course(
    user: CurrentUser,
    payload: dict,
    db: Session | None = Depends(get_db),
) -> dict[str, Any]:
    """Generate a private course for this learner from a stated goal. (M1)

    Body: {goal, n_lessons=4}

    Returns **202** with a job id, not a course. Generation is an outline call
    plus one call per lesson - measured at ~8s each, so 50-100s in total, well
    past the client's 30s timeout. Poll `GET /api/jobs/{job_id}`; on success its
    `result` carries `{course_id, slug, title, lessons, topics}` and the learner
    is already enrolled.

    The course is auto-published but private to them and marked
    `source="ai_generated"`. Nothing verifies that its content is correct - see
    CHECKLIST Slot 9C.

    Registered here rather than under /api/jobs so it mirrors
    POST /api/quizzes/generate; the asymmetry is that this one is asynchronous
    because it is an order of magnitude slower.
    """
    from app.services.course_planner import generate_course as _generate
    from app.services.jobs import JobLimitReached, create_job, schedule

    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured.",
        )

    try:
        user_uuid = uuid.UUID(str(user["id"]))
    except (KeyError, TypeError, ValueError) as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user."
        ) from err

    goal = str((payload or {}).get("goal") or "").strip()
    if len(goal) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tell us what you want to learn.",
        )

    n_lessons = (payload or {}).get("n_lessons", 4)

    try:
        job = create_job(
            db, user_uuid, "course", {"goal": goal[:400], "n_lessons": n_lessons}
        )
    except JobLimitReached as err:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(err)
        ) from err

    job_id = job.id

    async def _work(job_db, running_job):
        return await _generate(
            job_db,
            user_id=user_uuid,
            goal=goal,
            n_lessons=n_lessons,
            job_id=running_job.id,
        )

    # The task gets its own session: this request's session closes with the
    # response, a second from now.
    schedule(job_id, _work)

    return {
        "job_id": str(job_id),
        "status": "queued",
        "poll": f"/api/jobs/{job_id}",
    }


@router.post("/{course_id}/enroll")
def enroll(
    course_id: str,
    user: CurrentUser,
    db: Session | None = Depends(get_db),
) -> dict[str, Any]:
    """Enroll the current user in a course and emit course.enrolled."""
    if not db or not database_is_configured():
        return {"course_id": course_id, "enrolled": True}

    try:
        c_uuid = uuid.UUID(course_id)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid course ID.",
            headers={"X-Error-Code": "INVALID_COURSE_ID"},
        ) from err

    course = db.query(Course).filter(Course.id == c_uuid).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found.",
            headers={"X-Error-Code": "COURSE_NOT_FOUND"},
        )

    user_uuid = uuid.UUID(user["id"])
    existing = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user_uuid, Enrollment.course_id == c_uuid)
        .first()
    )

    if existing:
        return {
            "course_id": str(course.id),
            "enrolled": True,
            "already_enrolled": True,
            "enrollment_id": str(existing.id),
        }

    enrollment = Enrollment(user_id=user_uuid, course_id=c_uuid)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)

    emit(db, user_uuid, "course.enrolled", {"course_id": str(course.id)})

    return {
        "course_id": str(course.id),
        "enrolled": True,
        "already_enrolled": False,
        "enrollment_id": str(enrollment.id),
    }
