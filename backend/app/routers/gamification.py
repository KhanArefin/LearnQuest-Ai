"""XP, badges, streaks, challenges, leaderboard.

OWNER: Member 4. See plan.md 9.8.

These are stubs so the router graph is wired from day 1. Replace the bodies with
real implementations - keep the paths, they are the contract other members code against.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import CurrentUser
from app.models.gamification import UserStats
from app.services import xp_engine  # noqa: F401
from app.services.xp_engine import xp_for_level

router = APIRouter(prefix="/api", tags=["gamification"])


@router.get("/me/stats")
def my_stats(user: CurrentUser, db: Session | None = Depends(get_db)) -> dict:
    """Everything the dashboard header needs."""
    user_uuid = None
    if user and "id" in user:
        try:
            user_uuid = uuid.UUID(str(user["id"]))
        except ValueError:
            user_uuid = None

    if db is not None and user_uuid:
        stats = db.query(UserStats).filter(UserStats.user_id == user_uuid).first()
        if stats:
            next_xp = xp_for_level(stats.level + 1)
            return {
                "xp": stats.xp,
                "level": stats.level,
                "next_level_xp": next_xp,
                "coins": stats.coins,
                "current_streak": stats.current_streak,
                "longest_streak": stats.longest_streak,
                "total_learning_seconds": stats.total_learning_seconds,
            }

    return {
        "xp": 0,
        "level": 1,
        "next_level_xp": 283,
        "coins": 0,
        "current_streak": 0,
        "longest_streak": 0,
        "total_learning_seconds": 0,
    }


@router.get("/me/badges")
def my_badges(user: CurrentUser) -> dict:
    """Earned badges plus locked ones with progress toward them."""
    # TODO(M4): left join badges with user_badges.
    return {"earned": [], "locked": []}


@router.get("/challenges/today")
def todays_challenges(user: CurrentUser) -> dict:
    """Three challenges for today with the caller's progress."""
    # TODO(M4): lazily generate today's set on first request of the day.
    return {"items": []}


@router.post("/challenges/{challenge_id}/claim")
def claim_challenge(challenge_id: str, user: CurrentUser) -> dict:
    # TODO(M4): verify completion server-side before awarding.
    return {"challenge_id": challenge_id, "claimed": False, "xp_awarded": 0}


@router.get("/leaderboard")
def leaderboard(
    user: CurrentUser, scope: str = "global", period: str = "weekly"
) -> dict:
    """Top 50 plus the caller's own rank, pinned even when outside the top 50.

    Weekly sums xp_events over the window - which is why every award needs an event row.
    """
    # TODO(M4): respect preferences.leaderboard_opt_out.
    return {"items": [], "me": None, "scope": scope, "period": period}


@router.get("/notifications")
def notifications(user: CurrentUser) -> dict:
    return {"items": [], "unread": 0}


@router.post("/notifications/{notification_id}/read")
def mark_read(notification_id: str, user: CurrentUser) -> dict:
    return {"id": notification_id, "is_read": True}
