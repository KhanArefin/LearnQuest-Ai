"""Background generation jobs. OWNER: Member 1. See services/jobs.py.

A generic poll endpoint rather than one per feature: quiz generation and course
generation are both too slow for a request, and a client that already knows how
to poll `/api/jobs/{id}` needs no new code when the next slow thing arrives.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import CurrentUser
from app.services.jobs import DAILY_JOBS_PER_USER, get_job, jobs_used_today

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _require_db(db: Session | None) -> Session:
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured.",
        )
    return db


@router.get("/quota")
def my_quota(user: CurrentUser, db: Session | None = Depends(get_db)) -> dict[str, Any]:
    """How many generations this student has left today.

    Exposed so the UI can say so *before* they press a button, rather than
    letting them wait and then telling them no.
    """
    database = _require_db(db)
    used = jobs_used_today(database, uuid.UUID(user["id"]))
    return {
        "used": used,
        "limit": DAILY_JOBS_PER_USER,
        "remaining": max(0, DAILY_JOBS_PER_USER - used),
    }


@router.get("/{job_id}")
def poll_job(
    job_id: uuid.UUID,
    user: CurrentUser,
    db: Session | None = Depends(get_db),
) -> dict[str, Any]:
    """State of one job. 404 for a job that is not yours.

    `status` is queued | running | succeeded | failed. On success `result`
    carries the generated payload; on failure `error` is a sentence written for
    the student, not a stack trace.
    """
    database = _require_db(db)
    job = get_job(database, job_id, uuid.UUID(user["id"]))
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found."
        )
    return job.to_dict()


@router.get("")
def my_jobs(
    user: CurrentUser,
    db: Session | None = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    """This student's recent generations, newest first."""
    from app.models.ai import GenerationJob

    database = _require_db(db)
    rows = (
        database.query(GenerationJob)
        .filter(GenerationJob.user_id == uuid.UUID(user["id"]))
        .order_by(GenerationJob.created_at.desc())
        .limit(limit)
        .all()
    )
    return {"items": [r.to_dict() for r in rows], "total": len(rows)}
